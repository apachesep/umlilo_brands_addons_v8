# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web.http import Controller, route, request
from openerp.addons.web.controllers.main import _serialize_exception
from openerp.osv import osv
from openerp.tools import html_escape

import simplejson
from werkzeug import exceptions, url_decode
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse
from werkzeug.datastructures import Headers
from reportlab.graphics.barcode import createBarcodeDrawing


class ReportController(Controller):
    
    #------------------------------------------------------
    # Report controllers
    #------------------------------------------------------
    @route([
        '/report/<path:converter>/<reportname>',
        '/report/<path:converter>/<reportname>/<docids>',
    ], type='http', auth='user', website=True)
    def report_routes(self, reportname, docids=None, converter=None, **data):
        report_obj = request.registry['report']
        cr, uid, context = request.cr, request.uid, request.context

        if docids:
            docids = [int(i) for i in docids.split(',')]
        options_data = None
        if data.get('options'):
            options_data = simplejson.loads(data['options'])
        if data.get('context'):
            # Ignore 'lang' here, because the context in data is the one from the webclient *but* if
            # the user explicitely wants to change the lang, this mechanism overwrites it. 
            data_context = simplejson.loads(data['context'])
            if data_context.get('lang'):
                del data_context['lang']
            context.update(data_context)

        if converter == 'html':
            html = report_obj.get_html(cr, uid, docids, reportname, data=options_data, context=context)
            return request.make_response(html)
        elif converter == 'pdf':
            pdf = report_obj.get_pdf(cr, uid, docids, reportname, data=options_data, context=context)
            pdfhttpheaders = [('Content-Type', 'application/pdf'), ('Content-Length', len(pdf))]
            return request.make_response(pdf, headers=pdfhttpheaders)
        else:
            raise exceptions.HTTPException(description='Converter %s not implemented.' % converter)

    @route(['/report/download'], type='http', auth="user")
    def report_download(self, data, token):
        """This function is used by 'qwebactionmanager.js' in order to trigger the download of
        a pdf/controller report.

        :param data: a javascript array JSON.stringified containg report internal url ([0]) and
        type [1]
        :returns: Response with a filetoken cookie and an attachment header
        """
        requestcontent = simplejson.loads(data)
        url, type = requestcontent[0], requestcontent[1]
        try:
            if type == 'qweb-pdf':
                reportname = url.split('/report/pdf/')[1].split('?')[0]

                docids = None
                if '/' in reportname:
                    reportname, docids = reportname.split('/')

                if docids:
                    # Generic report:
                    response = self.report_routes(reportname, docids=docids, converter='pdf')
                else:
                    # Particular report:
                    data = url_decode(url.split('?')[1]).items()  # decoding the args represented in JSON
                    response = self.report_routes(reportname, converter='pdf', **dict(data))

############################## TO CHANGE NAME OF THE QWEB REPORT PDF FILE ##################

                if docids:
                    if reportname == "erp_umlilo_report.custom_invoice_report_template_id":
                        inv_obj = request.registry['account.invoice']
                        lst_inv = []
                        lst_inv = docids.split(",")
                        for ele_inv in lst_inv:
                            inv_browse = inv_obj.browse(request.cr, request.uid, [int(ele_inv)])
                            if inv_browse[0].type == 'out_invoice' or inv_browse[0].type == 'in_invoice':
                                if inv_browse[0].number:
                                    reportname = str(inv_browse[0].number or '') + '-' + str(inv_browse[0].name or '')
                                else:
                                    reportname = str(inv_browse[0].name or 'Invoice')
                            else:
                                if inv_browse[0].number:
                                    reportname = "Refund" + '-' + str(inv_browse[0].number or '') + '-' + str(inv_browse[0].name or '')
                                else:
                                    reportname = str(inv_browse[0].name or 'Refund')
                                    
                    if reportname == "erp_umlilo_report.custom_sale_order_template_id":
                        sale_obj = request.registry['sale.order']
                        lst = []
                        lst = docids.split(",")
                        for ele in lst:
                            sale_browse = sale_obj.browse(request.cr, request.uid, [int(ele)])
                            if sale_browse[0].state in ['draft', 'sent']:
                                if sale_browse[0].name:
                                    reportname = "Quote" + '-' + str(sale_browse[0].name) + '-' + str(sale_browse[0].client_order_ref or '')
                                else:
                                    reportname = "Quote" + str(sale_browse[0].client_order_ref or '')
                            else :
                                if sale_browse[0].name:
                                    reportname = "Sales Order" + '-' + str(sale_browse[0].name) + '-' + str(sale_browse[0].client_order_ref or '')
                                else:
                                    reportname = "Sales Order" + str(sale_browse[0].client_order_ref or '')
                                    
#########################################################################################                    

                response.headers.add('Content-Disposition', 'attachment; filename=%s.pdf;' % reportname)
                response.set_cookie('fileToken', token)
                return response
            elif type =='controller':
                reqheaders = Headers(request.httprequest.headers)
                response = Client(request.httprequest.app, BaseResponse).get(url, headers=reqheaders, follow_redirects=True)
                response.set_cookie('fileToken', token)
                return response
            else:
                return
        except Exception, e:
            se = _serialize_exception(e)
            error = {
                'code': 200,
                'message': "Odoo Server Error",
                'data': se
            }
            return request.make_response(html_escape(simplejson.dumps(error)))
