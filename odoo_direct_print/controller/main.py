from odoo import http
from odoo.addons.web.controllers.report import ReportController, request
import json
import werkzeug.exceptions

class ReportController(ReportController):

    @http.route(['/report/is_open_print_dialog'], type='json', auth="user")
    def is_open_print_dialog(self, report_ref):
        return request.env['ir.actions.report'].sudo()._get_report(report_ref).is_open_print_dialog()


    @http.route()
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report = request.env['ir.actions.report'].sudo()
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(',') if i.isdigit()]
        if data.get('options'):
            data.update(json.loads(data.pop('options')))
        if data.get('context'):
            data['context'] = json.loads(data['context'])
            context.update(data['context'])
        if converter == 'html':
            html = report.with_context(context)._render_qweb_html(reportname, docids, data=data)[0]
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report.with_context(context)._render_qweb_pdf(reportname, docids, data=data)[0]
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        elif converter == 'text':
            text = report.with_context(context)._render_qweb_text(reportname, docids, data=data)[0]
            texthttpheaders = [('Content-Type', 'text/plain'), ('Content-Length', len(text))]
            return request.make_response(text, headers=texthttpheaders)
        else:
            raise werkzeug.exceptions.HTTPException(description='Converter %s not implemented.' % converter)
