from openerp.report import report_sxw
from openerp.osv import osv
from datetime import time, date, datetime

class custom_invoice_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context=None):
        super(custom_invoice_report, self).__init__(cr, uid, name, context=context)
        self.index = 0
        self.localcontext.update({
                                  'time' : time,
                                  'get_qty_format' : self._get_qty_format,
                                  'get_date' : self._get_date,
                                  'get_width' : self._get_width,
                                  'get_height' : self._get_height,
                                  'get_job_number' : self._get_job_number
                                  })

    def _get_width(self, line):
        width1=str(line.width)
        width=width1.split('.')
        return width[0]

    def _get_height(self, line):
        height1=str(line.height)
        height=height1.split('.')
        return height[0]


    def _get_qty_format(self, obj):
        total_qty = 0.0
        for line in obj.invoice_line:
            total_qty = line.quantity
            qty = str(total_qty)
            qty1 = qty.split('.')
        return qty1[0]

    def _get_date(self, date_invoice):
        if date_invoice:
            d = datetime.strptime(date_invoice, '%Y-%m-%d')
            date1 = d.strftime('%d %B %Y')
            return date1

    def _get_job_number(self, invoice):
        sale_obj = self.pool.get('sale.order')
        purchase_obj = self.pool.get('purchase.order')
        invoice_obj = self.pool.get('account.invoice')
        print '\n _get_job_number',invoice,invoice.type
        if invoice:
            if invoice.type in ['out_invoice']:
                origin = invoice.origin
                sale_id = sale_obj.search(self.cr, self.uid, [('name', '=', origin)], context=None)
                if sale_id:
                    sale_brw = sale_obj.browse(self.cr, self.uid, sale_id[0], context=None)
                    return sale_brw.job_number
                    
            elif invoice.type in ['out_refund', 'in_refund']:
                origin = invoice.origin
                invoice_id = invoice_obj.search(self.cr, self.uid, [('number', '=', origin)], context=None)
                if invoice_id:
                    invoice_brw = invoice_obj.browse(self.cr, self.uid, invoice_id[0], context=None)
                if invoice.type in ['out_refund']:
                    sale_id = sale_obj.search(self.cr, self.uid, [('name', '=', invoice_brw.origin)], context=None)
                    if sale_id:
                        sale_brw = sale_obj.browse(self.cr, self.uid, sale_id[0], context=None)
                        return sale_brw.job_number
                else:
                    purchase_id = purchase_obj.search(self.cr, self.uid, [('name', '=', invoice_brw.origin)], context=None)
                    if purchase_id:
                        purchase_brw = purchase_obj.browse(self.cr, self.uid, purchase_id[0], context=None)
                        return purchase_brw.x_job_number
                    
            else:
                origin = invoice.origin
                purchase_id = purchase_obj.search(self.cr, self.uid, [('name', '=', origin)], context=None)
                if purchase_id:
                    purchase_brw = purchase_obj.browse(self.cr, self.uid, purchase_id[0], context=None)
                    print '\n \n get job nu',purchase_brw.x_job_number
                    return purchase_brw.x_job_number
                

class custom_invoice_report_template_id(osv.AbstractModel):
    _name='report.erp_umlilo_report.custom_invoice_report_template_id'
    _inherit='report.abstract_report'
    _template='erp_umlilo_report.custom_invoice_report_template_id'
    _wrapped_report_class=custom_invoice_report


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
