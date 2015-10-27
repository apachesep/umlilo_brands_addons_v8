from openerp.osv import osv,fields

class purchase_order(osv.osv):
    
    _name = "purchase.order"
    _inherit = "purchase.order"
    
    _columns = {
    
			'x_job_number' : fields.char('Job Number', size=5),
    }
    
    def print_quotation(self, cr, uid, ids, context=None):
        '''
        This function prints the request for quotation and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(ids) == 1, 'This option should only be used for a single id at a time'
        self.signal_workflow(cr, uid, ids, 'send_rfq')
        return self.pool['report'].get_action(cr, uid, ids, 'erp_umlilo_report.custom_purchase_order_report_template_id', context=context)
        
        
        

    
    
