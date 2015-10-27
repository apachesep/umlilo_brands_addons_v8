from openerp.osv import fields, osv

class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    
    def _get_invoice_vals(self, cr, uid, key, inv_type, journal_id, move, context=None):
        res = super(stock_picking, self)._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)
        sale_id = self.pool.get('sale.order').search(cr, uid, [('name', '=', move.origin)])
        if sale_id:
            sale_rec = self.pool.get('sale.order').browse(cr, uid, sale_id)
            res.update({'customer_po_no' : sale_rec.customer_po_no})
        return res
        
    
