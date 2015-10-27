from openerp.osv import osv, fields

class sale_order(osv.osv):

    _name = "sale.order"
    _inherit = "sale.order"

    _columns = {
            'customer_po_no' : fields.char('Customer PO No', size=10),
            'job_number' : fields.char('Job Number', size=5),


    }

    def print_quotation(self, cr, uid, ids, context=None):
        '''
        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        self.signal_workflow(cr, uid, ids, 'quotation_sent')
        return self.pool['report'].get_action(cr, uid, ids, 'erp_umlilo_report.custom_sale_order_template_id', context=context)

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        res = super(sale_order, self)._prepare_invoice(cr, uid, order, lines, context=context)
        res.update({'customer_po_no' : order.customer_po_no, 'x_job_number':order.job_number})
        return res

