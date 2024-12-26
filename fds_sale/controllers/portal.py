import logging
import json
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.sale.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager

_logger = logging.getLogger(__name__)


class CustomerPortal(portal.CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values.update({
            'partner':  request.env.user.partner_id
        })
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        SaleOrder = request.env['sale.order']
        if 'committed_quotation_count' in counters:
            values['committed_quotation_count'] = SaleOrder.search_count(self._prepare_committed_quotations_domain(partner)) \
                if SaleOrder.check_access_rights('read', raise_exception=False) else 0

        if 'estimate_quotation_count' in counters:
            values['estimate_quotation_count'] = SaleOrder.search_count(self._prepare_estimate_quotations_domain(partner)) \
                if SaleOrder.check_access_rights('read', raise_exception=False) else 0
        return values

    def _prepare_estimate_quotations_domain(self, partner):
        return [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['draft'])
        ]

    def _prepare_committed_quotations_domain(self, partner):
        return [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['committed'])
        ]
    
    def _get_sale_searchbar_inputs(self):
        return {
            'name': {'input': 'name', 'label': _('Search in Name')},
        }
    
    def _get_search_domain(self, search_in, search):
        search_domain = []
        if search_in in ('name'):
            search_domain = [('name', 'ilike', search)]
        return search_domain
    
    @http.route(['/my/equotes', '/my/equotes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_estimation_quotes(self, page=1, date_begin=None, search=None, search_in='name', date_end=None, sortby=None, **kw):
        """Estimation Quote."""
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        url = "/my/equotes"
        domain = self._prepare_estimate_quotations_domain(partner)

        searchbar_sortings = self._get_sale_searchbar_sortings()
        searchbar_inputs = self._get_sale_searchbar_inputs()

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        if search and search_in:
            domain += self._get_search_domain(search_in, search)

        # count for pager
        quotation_count = SaleOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['estimate_quotation_count'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'quotations': orders.sudo(),
            'page_name': 'equote',
            'pager': pager,
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
        })
        return request.render("fds_sale.portal_my_estimate_quotations", values)

    @http.route(['/my/cquotes', '/my/cquotes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_committed_quotes(self, page=1, date_begin=None, search=None, search_in='name', date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        url = "/my/cquotes"
        domain = self._prepare_committed_quotations_domain(partner)

        searchbar_sortings = self._get_sale_searchbar_sortings()
        searchbar_inputs = self._get_sale_searchbar_inputs()

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        if search and search_in:
            domain += self._get_search_domain(search_in, search)

        # count for pager
        quotation_count = SaleOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url=url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['committed_quotation_count'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'committed_quotations': orders.sudo(),
            'page_name': 'cquote',
            'pager': pager,
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
            'sortby': sortby,
        })
        return request.render("fds_sale.portal_my_committed_quotations", values)

    @http.route([
        '/my/orders/<int:order_id>',
    ], type='http', auth='public', website=True)
    def portal_order_page(self, order_id=None, **post):
        response = super(CustomerPortal, self).portal_order_page(order_id=order_id, **post)

        order = response.qcontext.get('sale_order', False)
        history = ''
        if history == 'my_orders_history':
            if order.state == 'committed':
                history = 'my_committed_quotations_history'
            elif order.state == 'draft':
                history = 'my_estimation_quotations_history'
            response.qcontext.update.update(get_records_pager(history, order))
        response.qcontext.update({
            'user': request.env.user,
        })
        return response

    @http.route(['/my/orders/<int:order_id>/commit'], type='http', auth="public", methods=['POST'], website=True)
    def portal_quote_commit(self, order_id, access_token=None, **kwargs):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if order_sudo.state in ('draft', 'sent') and request.env.user.partner_id.can_commit_quotation:
            order_sudo.action_commit()
            # _message_post_helper(
            #     'sale.order',
            #     order_sudo.id,
            #     commit_message,
            #     token=access_token,
            # )
            redirect_url = order_sudo.get_portal_url()
        else:
            redirect_url = order_sudo.get_portal_url(query_string="&message=cant_commit")

        return request.redirect(redirect_url)

    @http.route(['/my/orders/<int:order_id>/edit'], type='http', auth="user", methods=['GET', 'POST'], website=True)
    def portal_quote_edit(self, order_id, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day
        values = {
            'message': message
        }

        if request.httprequest.method == 'POST':
            try:
                self._save_edit_sale_order(order_sudo)
                redirect_url = order_sudo.get_portal_url(query_string="&message=edit_successful")
                return request.redirect(redirect_url)
            except Exception as ex:
                _logger.error(f"Error Editing sale order. {ex}")
                values['message'] = 'edit_failed'

        backend_url = f'/web#model={order_sudo._name}'\
                      f'&id={order_sudo.id}'\
                      f'&action={order_sudo._get_portal_return_action().id}'\
                      f'&view_type=form'
        
        line_product_custom_vals = {
            line.id: json.dumps([
                {
                    "custom_product_template_attribute_value_id": custom_attribute.custom_product_template_attribute_value_id.id,
                    "name": custom_attribute.name,
                    "custom_value": custom_attribute.custom_value
                }
                for custom_attribute in line.product_custom_attribute_value_ids
            ])
            for line in order_sudo.order_line
        }

        values.update({
            'sale_order': order_sudo,
            'token': access_token,
            'landing_route': '/shop/payment/validate',
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
            'report_type': 'html',
            'action': order_sudo._get_portal_return_action(),
            'line_product_custom_vals': line_product_custom_vals,
            'product_templates': request.env['product.template'].sudo().search([('sale_ok', '=', True),('company_id', 'in', [request.env.user.company_id.id, False])]),
            'backend_url': backend_url,
            'res_company': order_sudo.company_id,  # Used to display correct company logo
        })

        # Payment values
        if order_sudo._has_to_be_paid():
            values.update(self._get_payment_values(order_sudo))

        if order_sudo.state in ('draft', 'sent', 'cancel'):
            history_session_key = 'my_quotations_history'
        elif order_sudo.state == 'committed':
            history_session_key = 'my_committed_quotations_history'
        else:
            history_session_key = 'my_orders_history'

        values = self._get_page_view_values(
            order_sudo, access_token, values, history_session_key, False)

        return request.render('fds_sale.sale_order_portal_edit_template', values)

    def _save_edit_sale_order(self, order):
        # prevent cheater update other fields
        # mapping field and parser
        allow_update_fields = {
            'product_id': int,
            'product_uom_qty': float,
            'product_custom_attribute_value_ids': list
        }
        params = request.params
        post_line_values = {}
        # Build a dict with all values
        # Result:
        # {
        #     line.id: { update vals},
        #     new_line_id: { create vals}
        # }
        for k, v in params.items():
            if '-' in k:
                line_id, field = k.split('-')
                if field == 'custom_products':
                    field = 'product_custom_attribute_value_ids'
                    custom_products = json.loads(v)
                    v = []  # product_custom_attribute_value_ids
                    for custom_product in custom_products:
                        v.append({
                            'custom_product_template_attribute_value_id': custom_product['custom_product_template_attribute_value_id'],
                            'custom_value': custom_product['custom_value']
                        })

                if field in allow_update_fields:
                    v = allow_update_fields[field](v)
                    if line_id in post_line_values:
                        post_line_values[line_id].update({
                            field: v
                        })
                    else:
                        post_line_values[line_id] = {
                            field: v
                        }

        # Update lines
        order_line_vals = []
        for line in order.order_line:
            if (line_id := str(line.id)) in post_line_values:
                exist_custom_attribute_value_ids = {
                    custom_product.custom_product_template_attribute_value_id.id: custom_product.id
                    for custom_product in line.product_custom_attribute_value_ids
                }
                product_custom_attribute_value_ids = []
                for custom_product in post_line_values[line_id]['product_custom_attribute_value_ids']:
                    custom_attribute_value_id = custom_product['custom_product_template_attribute_value_id']
                    if line_custom_product_id := exist_custom_attribute_value_ids.get(custom_attribute_value_id, False):
                        # custom attribute exist => update
                        product_custom_attribute_value_ids.append((1, line_custom_product_id, {
                            'custom_value': custom_product['custom_value']
                        }))
                        del exist_custom_attribute_value_ids[custom_attribute_value_id]
                    else:
                        product_custom_attribute_value_ids.append((
                            0, 0, {
                                'custom_product_template_attribute_value_id': custom_attribute_value_id,
                                'custom_value': custom_product['custom_value']
                            })
                        )
                
                # remove the rest custom attribute
                for line_custom_id in exist_custom_attribute_value_ids.values():
                    product_custom_attribute_value_ids.append((2, line_custom_id))
                
                post_line_values[line_id]['product_custom_attribute_value_ids'] = product_custom_attribute_value_ids

                order_line_vals.append((1, int(line_id), post_line_values[line_id]))
                if line.product_id.id == post_line_values[line_id]['product_id']:
                    del post_line_values[line_id]['product_id']
                # Remove update line_id
                del post_line_values[line_id]

        # new create line
        for _id, vals in post_line_values.items():
            if '_new' in _id:
                product_custom_attribute_value_ids = []
                for custom_product in vals['product_custom_attribute_value_ids']:
                    product_custom_attribute_value_ids.append((
                        0, 0, {
                            'custom_product_template_attribute_value_id': custom_product['custom_product_template_attribute_value_id'],
                            'custom_value': custom_product['custom_value']
                        })
                    )
                vals['product_custom_attribute_value_ids'] = product_custom_attribute_value_ids
                order_line_vals.append((0, 0, vals))

        # Delete lines
        if delete_ids := params.get('temp-js_temp_delete_line', ''):
            delete_ids = delete_ids.split(',')
            for delete_id in delete_ids:
                order_line_vals.append((2, int(delete_id)))

        if order_line_vals:
            order.order_line = order_line_vals
            if order.state == 'sent':
                order.action_draft()

    def _prepare_sale_portal_rendering_values(
        self, page=1, date_begin=None, date_end=None, sortby=None, quotation_page=False, **kwargs
    ):
        values = super(CustomerPortal, self)._prepare_sale_portal_rendering_values(
            page=page, date_begin=date_begin, date_end=date_end, sortby=sortby, quotation_page=quotation_page, **kwargs)
        searchbar_sortings = values['searchbar_sortings']
        url = values['default_url']
        sortby = values['sortby']
        SaleOrder = request.env['sale.order']
        partner = request.env.user.partner_id

        searchbar_inputs = self._get_sale_searchbar_inputs()

        if quotation_page:
            domain = self._prepare_quotations_domain(partner)
        else:
            domain = self._prepare_orders_domain(partner)

        search = kwargs.get('search', None)
        search_in = kwargs.get('search_in', 'name')
        if search and search_in:
            domain += self._get_search_domain(search_in, search)

        sort_order = searchbar_sortings[sortby]['order']

        pager_values = portal_pager(
            url=url,
            total=SaleOrder.search_count(domain),
            page=page,
            step=self._items_per_page,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
        )
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager_values['offset'])

        values.update({
            'quotations': orders.sudo() if quotation_page else SaleOrder,
            'orders': orders.sudo() if not quotation_page else SaleOrder,
            'pager': pager_values,
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'search': search,
        })
        return values
