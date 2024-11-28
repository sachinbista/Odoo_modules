import datetime
import functools
import io
import itertools
import json
import logging
import operator
from collections import OrderedDict

from werkzeug.exceptions import InternalServerError

import odoo
import odoo.modules.registry
from odoo import http
from odoo.exceptions import UserError
from odoo.http import content_disposition, request
from odoo.tools import lazy_property, osutil, pycompat
from odoo.tools.misc import xlsxwriter
from odoo.tools.translate import _


_logger = logging.getLogger(__name__)

from odoo.addons.web.controllers import export as export_portal

def none_values_filtered(func):
    @functools.wraps(func)
    def wrap(iterable):
        return func(v for v in iterable if v is not None)
    return wrap


def allow_empty_iterable(func):
    """
    Some functions do not accept empty iterables (e.g. max, min with no default value)
    This returns the function `func` such that it returns None if the iterable
    is empty instead of raising a ValueError.
    """
    @functools.wraps(func)
    def wrap(iterable):
        iterator = iter(iterable)
        try:
            value = next(iterator)
            return func(itertools.chain([value], iterator))
        except StopIteration:
            return None
    return wrap


OPERATOR_MAPPING = {
    'max': none_values_filtered(allow_empty_iterable(max)),
    'min': none_values_filtered(allow_empty_iterable(min)),
    'sum': sum,
    'bool_and': all,
    'bool_or': any,
}
class GroupsTreeNode:
    """
    This class builds an ordered tree of groups from the result of a `read_group(lazy=False)`.
    The `read_group` returns a list of dictionnaries and each dictionnary is used to
    build a leaf. The entire tree is built by inserting all leaves.
    """

    def __init__(self, model, fields, groupby, groupby_type, root=None):
        self._model = model
        self._export_field_names = fields  # exported field names (e.g. 'journal_id', 'account_id/name', ...)
        self._groupby = groupby
        self._groupby_type = groupby_type

        self.count = 0  # Total number of records in the subtree
        self.children = OrderedDict()
        self.data = []  # Only leaf nodes have data

        if root:
            self.insert_leaf(root)

    def _get_aggregate(self, field_name, data, group_operator):
        # When exporting one2many fields, multiple data lines might be exported for one record.
        # Blank cells of additionnal lines are filled with an empty string. This could lead to '' being
        # aggregated with an integer or float.
        data = (value for value in data if value != '')

        if group_operator == 'avg':
            return self._get_avg_aggregate(field_name, data)

        aggregate_func = OPERATOR_MAPPING.get(group_operator)
        if not aggregate_func:
            _logger.warning("Unsupported export of group_operator '%s' for field %s on model %s", group_operator, field_name, self._model._name)
            return

        if self.data:
            return aggregate_func(data)
        return aggregate_func((child.aggregated_values.get(field_name) for child in self.children.values()))

    def _get_avg_aggregate(self, field_name, data):
        aggregate_func = OPERATOR_MAPPING.get('sum')
        if self.data:
            return aggregate_func(data) / self.count
        children_sums = (child.aggregated_values.get(field_name) * child.count for child in self.children.values())
        return aggregate_func(children_sums) / self.count

    def _get_aggregated_field_names(self):
        """ Return field names of exported field having a group operator """
        aggregated_field_names = []
        for field_name in self._export_field_names:
            if field_name == '.id':
                field_name = 'id'
            if '/' in field_name:
                # Currently no support of aggregated value for nested record fields
                # e.g. line_ids/analytic_line_ids/amount
                continue
            field = self._model._fields[field_name]
            if field.group_operator:
                aggregated_field_names.append(field_name)
        return aggregated_field_names

    # Lazy property to memoize aggregated values of children nodes to avoid useless recomputations
    @lazy_property
    def aggregated_values(self):

        aggregated_values = {}

        # Transpose the data matrix to group all values of each field in one iterable
        field_values = zip(*self.data)
        for field_name in self._export_field_names:
            field_data = self.data and next(field_values) or []

            if field_name in self._get_aggregated_field_names():
                field = self._model._fields[field_name]
                aggregated_values[field_name] = self._get_aggregate(field_name, field_data, field.group_operator)

        return aggregated_values

    def child(self, key):
        """
        Return the child identified by `key`.
        If it doesn't exists inserts a default node and returns it.
        :param key: child key identifier (groupby value as returned by read_group,
                    usually (id, display_name))
        :return: the child node
        """
        if key not in self.children:
            self.children[key] = GroupsTreeNode(self._model, self._export_field_names, self._groupby, self._groupby_type)
        return self.children[key]

    def insert_leaf(self, group):
        """
        Build a leaf from `group` and insert it in the tree.
        :param group: dict as returned by `read_group(lazy=False)`
        """
        leaf_path = [group.get(groupby_field) for groupby_field in self._groupby]
        domain = group.pop('__domain')
        count = group.pop('__count')

        records = self._model.search(domain, offset=0, limit=False, order=False)

        # Follow the path from the top level group to the deepest
        # group which actually contains the records' data.
        node = self # root
        node.count += count
        for node_key in leaf_path:
            # Go down to the next node or create one if it does not exist yet.
            node = node.child(node_key)
            # Update count value and aggregated value.
            node.count += count

        node.data = records.export_data(self._export_field_names).get('datas', [])

class CustomCSVExport(export_portal.CSVExport, http.Controller):
    def base(self, data):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        if model == 'product.product' and not request.env.user.has_group(
                'bista_contact_product_manager.product_cost_restriction'):
            fields = [field for field in fields if field['name'] != 'standard_price']

        Model = request.env[model].with_context(import_compat=import_compat, **params.get('context', {}))
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.with_context(active_test=False).read_group(domain, ['__count'], groupby, lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree)
        else:
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas', [])
            response_data = self.from_data(columns_headers, export_data)

        # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(response_data,
                                     headers=[('Content-Disposition',
                                               content_disposition(
                                                   osutil.clean_filename(self.filename(model) + self.extension))),
                                              ('Content-Type', self.content_type)],
                                     )


class CustomExcelExport(export_portal.ExcelExport, http.Controller):

    def base(self, data):
        params = json.loads(data)
        model, fields, ids, domain, import_compat = \
            operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)

        if model == 'product.product' and not request.env.user.has_group(
                'bista_contact_product_manager.product_cost_restriction'):
            fields = [field for field in fields if field['name'] != 'standard_price']

        Model = request.env[model].with_context(import_compat=import_compat, **params.get('context', {}))
        if not Model._is_an_ordinary_table():
            fields = [field for field in fields if field['name'] != 'id']

        field_names = [f['name'] for f in fields]
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]

        groupby = params.get('groupby')
        if not import_compat and groupby:
            groupby_type = [Model._fields[x.split(':')[0]].type for x in groupby]
            domain = [('id', 'in', ids)] if ids else domain
            groups_data = Model.with_context(active_test=False).read_group(domain, ['__count'], groupby, lazy=False)

            # read_group(lazy=False) returns a dict only for final groups (with actual data),
            # not for intermediary groups. The full group tree must be re-constructed.
            tree = GroupsTreeNode(Model, field_names, groupby, groupby_type)
            for leaf in groups_data:
                tree.insert_leaf(leaf)

            response_data = self.from_group_data(fields, tree)
        else:
            records = Model.browse(ids) if ids else Model.search(domain, offset=0, limit=False, order=False)

            export_data = records.export_data(field_names).get('datas', [])
            response_data = self.from_data(columns_headers, export_data)

        # TODO: call `clean_filename` directly in `content_disposition`?
        return request.make_response(response_data,
                                     headers=[('Content-Disposition',
                                               content_disposition(
                                                   osutil.clean_filename(self.filename(model) + self.extension))),
                                              ('Content-Type', self.content_type)],
                                     )


# class CustomExcelExport(export_portal.ExcelExport, http.Controller):
#
#     @http.route('/web/export/xlsx', type='http', auth="user")
#     def web_export_xlsx(self, data):
#         try:
#             params = json.loads(data)
#             model, fields, ids, domain, import_compat = \
#                 operator.itemgetter('model', 'fields', 'ids', 'domain', 'import_compat')(params)
#
#             if model == 'product.product' and not request.env.user.has_group('bista_contact_product_manager.product_cost_restriction'):
#                 fields = [field for field in fields if field['name'] != 'standard_price']
#                 params['fields'] = fields
#                 data = str(params)
#                 # corrected_string = data.replace("'", '"')
#                 # data = corrected_string
#             return self.base(data)
#         except Exception as exc:
#             _logger.exception("Exception during request handling.")
#             payload = json.dumps({
#                 'code': 200,
#                 'message': "Odoo Server Error",
#                 'data': http.serialize_exception(exc)
#             })
#             raise InternalServerError(payload) from exc
