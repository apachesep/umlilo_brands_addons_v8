from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.translate import _

class stock_history(osv.osv):
    _inherit = 'stock.history'
    
    
    def _get_inventory_value(self, cr, uid, ids, name, attr, context=None):
        if context is None:
            context = {}
        date = context.get('history_date')
        product_tmpl_obj = self.pool.get("product.template")
        product_uom_obj = self.pool.get('product.uom')
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.product_id.cost_method == 'real':
                res[line.id] = line.quantity * line.price_unit_on_quant
            else:
                print '\n\ndone'
                std_price = product_tmpl_obj.get_history_price(cr, uid, line.product_id.product_tmpl_id.id, line.company_id.id, date=date, context=context)
                prod_temp_obj = product_tmpl_obj.browse(cr, uid, line.product_id.product_tmpl_id.id)
                factor = product_uom_obj.browse(cr, uid, prod_temp_obj.uom_po_id.id).factor
                res[line.id] = line.quantity * (std_price * factor)
        return res
    
