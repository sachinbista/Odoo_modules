from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools import mute_logger

import logging
import psycopg2
import functools

_logger = logging.getLogger(__name__)

operation_merged = "Merged"
operation_update = "Updated"
operation_created = "Created"
operation_unlinked = "Deleted"


class MergeGroup(models.Model):
    _inherit = 'data_merge.group'

    def merge_records(self, records=None):
        self.ensure_one()
        if records is None:
            records = []

        domain = [
            ('group_id', '=', self.id),
            ('is_discarded', '=', self.env.context.get('show_discarded', False)),
        ]

        if records:
            domain += [('id', 'in', records)]

        to_merge = self.env['data_merge.record'].with_context(active_test=False).search(domain, order='id')
        self._merge_records(to_merge)

    def _merge_records(self, to_merge):
        logs = []
        to_merge_count = len(to_merge)
        if to_merge_count <= 1:
            return

        master_record = to_merge.filtered('is_master') or to_merge[0]
        to_merge = to_merge - master_record

        # Model Config
        model = master_record.model_id.res_model_id
        model_name = model.model
        model_env = self.env[model_name]

        # Record Config
        master_record_obj = model_env.browse(master_record.res_id)
        to_merge_records = model_env.browse(to_merge.mapped("res_id"))
        logs.append(
            self._get_merge_count(operation_merged, model_name, ",".join(to_merge_records.mapped("display_name"))))
        product_log = self._product_merge(model_name, master_record_obj, to_merge_records)
        self._contact_merge(model_name, master_record_obj, to_merge_records)

        # Merge field values
        merge_field_log = self._merge_fields(model, master_record_obj, to_merge_records)
        static_field_log = self._update_reference_fields(model, master_record_obj, to_merge_records)

        logs += product_log
        logs += merge_field_log
        logs += static_field_log
        # PSQL QUERY
        query, rel_log = self._get_relational_field_sql_query(model_name, master_record_obj, to_merge_records)

        logs += rel_log



        # Odoo Default Behavior
        if hasattr(model, '_merge_method'):
            merge = getattr(model, '_merge_method')
        else:
            merge = self._merge_method
        res = merge(master_record._original_records(), to_merge._original_records())

        # Unlink data duplication records
        is_merge_action = master_record.model_id.is_contextual_merge_action
        (master_record + to_merge).unlink()

        if query:
            self.env.cr.execute(query)

        # Check if merged records can be archived otherwise unlink
        logs += self._archive_merged_records(model, to_merge_records)

        try:
            message = "<strong>Merge Summary</strong><br/><ul>"
            message += "".join([f"<li>{line}</li>" for line in logs])
            message += "</ul>"
            master_record_obj.message_post(body=message)
        except Exception as e:
            _logger.info("Failed to post merge message ", e)

        return {
            'records_merged': res['records_merged'] if res.get('records_merged') else to_merge_count,
            'back_to_model': is_merge_action
        }

    def _archive_merged_records(self, model, to_merge):
        """
            Search for the active field in the model
            Active Exists: archive to merge records
            Active Not Exists: Unlink to merge records
        """
        ir_model_fields = self.env['ir.model.fields']
        model_name = model.model
        archive_field = ir_model_fields.search(
            [('model_id', '=', model.id),
             ('name', '=', 'active'),
             ('ttype', '=', 'boolean')])

        if archive_field:
            to_merge.write({'active': False})
            action = "Archived"
            _logger.info(f"Records merged and archived {model_name}: {to_merge.ids}")
        else:
            action = operation_unlinked
            to_merge.unlink()
        return [self._get_merge_count(action, model_name, ",".join(to_merge.mapped("display_name")))]

    def _get_relational_field_sql_query(self, model_name, master_record, to_merge):
        """
            Get all Many2one/Many2many fields of the model
            Generate SQY query to update to merge ids with master record id
            Avoid updating product variant due to product template constraints
            Avoid update sql views
            return Logs
        """

        logs = []
        ir_model_fields = self.env['ir.model.fields']
        rel_field_list = ir_model_fields.search(
            [('model_id.transient', '=', False),
             ('relation', '=', model_name),
             ('store', '=', True)])

        many2one = rel_field_list.filtered(lambda x: x.ttype == 'many2one')
        many2many = rel_field_list.filtered(lambda x: x.ttype == 'many2many')
        to_merge_ids = ",".join([str(line.id) for line in to_merge])

        query = ""
        relational_fields = []

        for m2o in many2one:
            source_model = m2o.model_id.model.replace(".", "_")

            # Exclude product_product table due to product template unique constraints
            if source_model == 'product_product':
                continue

            # Continue if the referenced object is not a SQL table
            is_table = self.is_table(source_model)

            if not is_table:
                continue

            m2o_domain = [(m2o.name, 'in', to_merge.ids)]
            record = self.env[m2o.model_id.model].sudo().search(m2o_domain)

            if not record:
                continue

            relational_fields.append(m2o.model_id.model)
            query += f"Update {source_model} " \
                     f"set {m2o.name} = '{master_record.id}' " \
                     f"where {m2o.name} in ({to_merge_ids});"

        for m2m in many2many:
            m2m_domain = [(m2m.name, 'in', to_merge.ids)]
            record = self.env[m2m.model_id.model].sudo().search(m2m_domain)

            if not record or m2m.relation_table in ['stock_route_product']:
                continue

            relational_fields.append(m2m.model_id.model)

            query += f"Update {m2m.relation_table} " \
                     f"set {m2m.column2} = '{master_record.id}' " \
                     f"where {m2m.column2} in ({to_merge_ids});"

            relational_fields.append(m2m.relation_table)

        if relational_fields:
            logs.append(self._get_merge_count(operation_update, "Relational Fields", ','.join(relational_fields)))
        return query, logs

    @api.model
    def _contact_merge(self, model_name, master_record, to_merge_records):
        """
            Ensure mail channel has unique partner ids
        """
        if model_name != 'res.partner':
            return
        channels_to_add = []
        for partner in to_merge_records:
            for channel in partner.channel_ids:
                if channel.id not in master_record.channel_ids.ids:
                    channels_to_add.append(channel.id)
        master_record.write({'channel_ids': [(4, channel) for channel in channels_to_add]})
        to_merge_records.write({'channel_ids': [(6, 0, [])]})

    @api.model
    def _product_merge(self, model_name, master_record, to_merge_records):
        """
            If product Template, Merge product variant first
                Ensure Reorder rule unique location,product constraints is not violated by unlinking duplicated rules.
            Validate product template tracking is same
            Validate product unit of measure is same
            Merge quant for non tracking products
            return Log
        """
        tag = "Product Merge:"
        logs = []

        if model_name not in ['product.template', 'product.product']:
            return logs

        quant_env = self.env['stock.quant']

        if model_name == 'product.template':
            master_variant = master_record.product_variant_id
            to_merge_variant = to_merge_records.mapped("product_variant_id")
            product_records = (master_variant | to_merge_variant)

            self.env['data_merge.record'].action_deduplicates(product_records)
            merge_data = self.env['data_merge.record'].search(
                [('res_model_name', '=', 'product.product'), ('res_id', 'in', product_records.ids)])
            merge_data.filtered(lambda x: x.res_id == master_variant.id).write({'is_master': True})

            stock_order_points = self.env['stock.warehouse.orderpoint']
            master_reorder_rules = stock_order_points.search([('product_id', '=', master_variant.id)])
            master_reorder_rule_locations = master_reorder_rules.mapped('location_id')
            to_merge_rules = stock_order_points.search([('product_id', 'in', to_merge_variant.ids)])
            duplicated_rules = to_merge_rules.filtered(lambda rule: rule.location_id in master_reorder_rule_locations)
            to_update_rules = to_merge_rules - duplicated_rules
            duplicated_rules.unlink()
            to_update_rules.write({'product_id': master_variant.id})

            if to_merge_variant:
                logs.append(self._get_merge_count(operation_update, "Product Variant", len(to_merge_variant)))
            if to_update_rules:
                logs.append(self._get_merge_count(operation_update, "Reorder Rule", len(to_update_rules)))
            if duplicated_rules:
                logs.append(self._get_merge_count(operation_unlinked, "Reorder Rule", len(duplicated_rules)))
            self._merge_records(merge_data)

        if not master_record:
            _logger.info(f"{tag} Master Product not found returning")
            return logs

        if not to_merge_records:
            _logger.info(f"{tag} To merge Product list is empty returning")
            return logs

        if model_name != 'product.product':
            return logs

        master_tracking = master_record.tracking
        different_tracking = to_merge_records.filtered(lambda x: x.tracking != master_tracking)
        to_merge_product_name = to_merge_records.mapped('name')

        if different_tracking:
            to_merge_tracking_types = to_merge_records.mapped('tracking')
            raise ValidationError(f"Some of the products to merge, does not have the same tracking as master.\n"
                                  f"Master Tracking Type: {master_record.display_name} - {master_tracking}\n"
                                  f"To Merge Tracking Type: {list(zip(to_merge_product_name, to_merge_tracking_types))}")

        master_uom_id = master_record.uom_id.id
        different_uom = to_merge_records.filtered(lambda x: x.uom_id.id != master_uom_id)
        if different_uom:
            to_merge_uom = set(','.join([line.uom_id.display_name for line in to_merge_records]))
            raise ValidationError(f"Some of the products to merge, does not have the same unit of measure as master.\n"
                                  f"Master Unite of measure: {master_tracking} - {master_record.display_name}\n"
                                  f"To Merge Unit of Measures: {to_merge_uom} - {to_merge_product_name}")

        if master_tracking != 'none':
            return logs

        to_merge_quants = quant_env.search([('product_id', 'in', to_merge_records.ids), ('quantity', '!=', False)])
        location_list = {}

        master_quant = quant_env.search(
            [('location_id', '!=', False),
             ('product_id', '=', master_record.id),
             ('quantity', '!=', 0),
             ], limit=1)

        quant_to_apply_ids = []

        for quant in to_merge_quants:
            location_id = quant.location_id.id
            if location_id not in location_list.keys():
                location_list[location_id] = 0
            location_list[location_id] += quant.quantity

        to_merge_quants.write({'inventory_quantity': 0})
        to_merge_quants.action_apply_inventory()

        for location in location_list:
            master_location_quant = master_quant.filtered(lambda x: x.location_id.id == location)
            location_quantity = location_list[location]

            if not location_quantity:
                continue

            if master_location_quant:
                if master_location_quant.product_uom_id.id != master_uom_id:
                    raise ValidationError("Stock quant has different unit of measure than master product uom.")
                master_location_quant.write({'inventory_quantity': master_location_quant.quantity + location_quantity})
            else:
                master_location_quant = quant_env.create({
                    'product_id': master_record.id,
                    'location_id': location,
                    'product_uom_id': master_uom_id,
                    'inventory_quantity': location_quantity
                })

            if master_location_quant.inventory_quantity:
                quant_to_apply_ids.append(master_location_quant.id)

        quants_to_apply = quant_env.browse(quant_to_apply_ids)
        quants_to_apply.action_apply_inventory()

        logs.append(
            self._get_merge_count(operation_merged, "Inventory Count", len(quants_to_apply) + len(to_merge_quants)))

        return logs

    @api.model
    def is_table(self, table):
        table_type_query = f"select table_type from information_schema.tables where table_name = '{table}'"
        self.env.cr.execute(table_type_query)
        res = self.env.cr.fetchone()
        if res and res[0] == 'BASE TABLE':
            return True
        return

    @api.model
    def _get_empty_vals(self, record, fields):
        vals = []
        for field in fields:
            try:
                if not record[field.name]:
                    vals.append(field)
            except Exception as e:
                _logger.warning("Exception Empty Vals Func: ", e)

        return vals

    @api.model
    def _get_empty_field_value(self, empty_fields_list, records_to_merge):
        """
            Add value of to merge records to master record if master record field is empty
            Take the first found value and exempt the field from overwrite by the next record.
        """
        vals = {}
        field_added = []
        for rec in records_to_merge:
            for field in empty_fields_list:
                if field.name in field_added:
                    continue

                value = rec[field.name]
                if value:
                    if field.ttype == 'many2one':
                        value = rec[field.name].id
                    elif field.ttype == 'many2many':
                        value = [(4, rec_id) for rec_id in rec[field.name].ids]
                    vals[field.name] = value
        return vals

    @api.model
    def _merge_fields(self, model, master, to_merge):
        constraint_fields = self._get_constraint_fields(self.env[model.model])
        if model.model == 'product.template':
            product_model = self.env['product.product']
            constraint_fields += self._get_constraint_fields(product_model)
        elif model.model == 'product.product':
            product_model = self.env['product.product']
            constraint_fields += self._get_constraint_fields(product_model)

        fields = self.env['ir.model.fields'].search(
            [('name', 'not in', constraint_fields), ('model_id', '=', model.id), ('readonly', '=', False),
             ('ttype', '!=', 'one2many')])
        empty_fields_list = self._get_empty_vals(master, fields)
        vals = self._get_empty_field_value(empty_fields_list, to_merge)
        master.write(vals)
        if vals.keys():
            return [self._get_merge_count(operation_update, "Master Record Fields", ', '.join(vals.keys()))]
        return []

    @api.model
    def _get_constraint_fields(self, model):
        constraints = model._sql_constraints
        constraint_fields = []
        for rec in constraints:
            rule = rec[1].lower()
            if "unique" in rule:
                field = rule.replace("unique(", "").replace(")", "")

                if "," in field:
                    constraint_fields += field.split(',')
                    continue

                constraint_fields.append(field)
        return constraint_fields

    @api.model
    def _update_reference_fields(self, model, master, to_merge):
        """Update all reference fields from the src_object to dst_object.
        :param src_objects : merge source res.object recordset (does not include destination one)
        :param dst_object : record of destination res.object
        """
        _logger.debug("_update_reference_fields for master: %s for to merge: %r", master.id, to_merge.ids)
        logs = []

        def update_records(model, to_merge, field_model="model", field_id="res_id"):
            Model = self.env[model] if model in self.env else None

            if Model is None:
                return

            records = Model.sudo().search([(field_model, "=", model), (field_id, "=", to_merge.ids)])
            if records:
                logs.append(self._get_merge_count(operation_update, model, len(records)))
            try:
                with mute_logger("odoo.sql_db"), self.env.cr.savepoint():
                    records.sudo().write({field_id: master.id})
                    records.flush()
            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent object_id is useless, better delete it
                records.sudo().unlink()

        update_records = functools.partial(update_records)

        update_records("calendar.event", to_merge=to_merge, field_model="res_model")
        update_records("ir.attachment", to_merge=to_merge, field_model="res_model")
        update_records("mail.followers", to_merge=to_merge, field_model="res_model")
        update_records("portal.share", to_merge=to_merge, field_model="res_model")
        update_records("rating.rating", to_merge=to_merge, field_model="res_model")
        update_records("mail.activity", to_merge=to_merge, field_model="res_model")
        update_records("mail.message", to_merge=to_merge)
        update_records("ir.model.data", to_merge=to_merge)

        records = self.env["ir.model.fields"].search([("ttype", "=", "reference")])

        for record in records.sudo():
            try:
                Model = self.env[record.model]
                field = Model._fields[record.name]
            except KeyError:
                # unknown model or field => skip
                continue

            if field.compute is not None:
                continue

            reference_fields = [f"{model.model},{line}" for line in to_merge.ids]
            records_ref = Model.sudo().search([(record.name, "in", reference_fields)])
            values = {
                record.name: "%s,%d" % (model.model, master.id),
            }
            records_ref.sudo().write(values)

        self.flush()
        return logs

    def _get_merge_count(self, operation, key, value):
        if value:
            value = str(value).replace(".", " ").replace("_", " ").title()
        return f"{operation}: {key} ({value})"

