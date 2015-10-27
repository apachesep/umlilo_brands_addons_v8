from openerp.osv import osv, fields
from datetime import datetime, timedelta
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT

import openerp.addons.decimal_precision as dp
from openerp import api

class sale_order(osv.osv):
    
    _inherit = "sale.order"
    
    def _amount_line_tax(self, cr, uid, line, context=None):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, line.tax_id, line.price_unit * (1-(line.discount or 0.0)/100.0), line.product_uom_qty * line.m2, line.product_id, line.order_id.partner_id)['taxes']:
            val += c.get('amount', 0.0)
        return val
    
    _columns = {
                'dispatch_type' : fields.selection([('deliver','Deliver'),('collect','Collect'),('Courier','courier')],'Dispatch Type'),
                }
    

class  sale_order_line(osv.osv):
    
    _inherit = "sale.order.line"
    
    def _amount_line(self, cr, uid, ids, field_name, arg, context=None):
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        res = {}
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            quantity = line.product_uom_qty * line.m2
            taxes = tax_obj.compute_all(cr, uid, line.tax_id, price, quantity, line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            
            res[line.id] = cur_obj.round(cr, uid, cur, taxes['total'])
        return res
    
    def _get_m2(self,cr,uid,ids,field,arg,context=None):
        res = {}
        print ids
        for record in self.browse(cr,uid,ids):
            if record.width == 0.00 or record.height == 0.00:
                res[record.id] = 1.00
            else:
                res[record.id] = (record.width * record.height) / 1000000
        return res
    def _get_net_price(self,cr,uid,ids,field,arg,context=None):
        res = {}
        print ids
        for record in self.browse(cr,uid,ids):
            if record.width == 0.00 or record.height == 0.00:
                res[record.id] = record.price_unit * record.product_uom_qty
            else:
                res[record.id] = ((record.width * record.height) / 1000000) * record.price_unit * record.product_uom_qty
        return res
    
    _columns = {
                'width':fields.float('Width', required='True'),
                'height': fields.float('Height', required='True'),
                'm2' : fields.function(_get_m2,type='float',string='M2'),
                'net_price':fields.function(_get_net_price, type="float", string="Net Price"),
                'price_subtotal': fields.function(_amount_line, string='Subtotal', digits_compute= dp.get_precision('Account')),
                }
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        """Prepare the dict of values to create the new invoice line for a
           sales order line. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record line: sale.order.line record to invoice
           :param int account_id: optional ID of a G/L account to force
               (this is used for returning products including service)
           :return: dict of values to create() the invoice line
        """
        res = {}
        if not line.invoiced:
            if not account_id:
                if line.product_id:
                    account_id = line.product_id.property_account_income.id
                    if not account_id:
                        account_id = line.product_id.categ_id.property_account_income_categ.id
                    if not account_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please define income account for this product: "%s" (id:%d).') % \
                                    (line.product_id.name, line.product_id.id,))
                else:
                    prop = self.pool.get('ir.property').get(cr, uid,
                            'property_account_income_categ', 'product.category',
                            context=context)
                    account_id = prop and prop.id or False
            uosqty = self._get_line_qty(cr, uid, line, context=context)
            uos_id = self._get_line_uom(cr, uid, line, context=context)
            pu = 0.0
            if uosqty:
                pu = round(line.price_unit * line.product_uom_qty / uosqty,
                        self.pool.get('decimal.precision').precision_get(cr, uid, 'Product Price'))
            fpos = line.order_id.fiscal_position or False
            account_id = self.pool.get('account.fiscal.position').map_account(cr, uid, fpos, account_id)
            if not account_id:
                raise osv.except_osv(_('Error!'),
                            _('There is no Fiscal Position defined or Income category account defined for default properties of Product categories.'))
            res = {
                'name': line.name,
                'sequence': line.sequence,
                'origin': line.order_id.name,
                'account_id': account_id,
                'price_unit': pu,
                'quantity': uosqty,
                'discount': line.discount,
                'uos_id': uos_id,
                'product_id': line.product_id.id or False,
                'invoice_line_tax_id': [(6, 0, [x.id for x in line.tax_id])],
                'account_analytic_id': line.order_id.project_id and line.order_id.project_id.id or False,
                'width':line.width,
                'height':line.height,
            }
            

        return res
    
class account_invoice(osv.osv):
    
    _inherit = "account.invoice"

    def _amount_get_balance(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys(ids, 0.0)
        for invoice in self.browse(cr, uid, ids, context=context):
            cust_invoice_ids = self.search(cr,uid,[('id','<=',int(invoice.id)),('type','=','out_invoice'),('state','=','open'),('partner_id','=',invoice.partner_id and invoice.partner_id.id or False)],context=context)
            if cust_invoice_ids:
                total = sum([self.browse(cr,uid,x,context=context).residual for x in cust_invoice_ids])
                res[invoice.id]= total
        return res

    def _amount_get_balance_supplier(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        if not ids:
            ids = self.search(cr, uid, [])
        res = {}.fromkeys(ids, 0.0)
        for invoice in self.browse(cr, uid, ids, context=context):
            supplier_invoice_ids = self.search(cr,uid,[('id','<=',int(invoice.id)),('type','=','in_invoice'),('state','=','open'),('partner_id','=',invoice.partner_id and invoice.partner_id.id or False)],context=context)
            if supplier_invoice_ids:
                supplier_total = sum([self.browse(cr,uid,x,context=context).residual for x in supplier_invoice_ids])
                res[invoice.id]= supplier_total
        return res


    
    _columns = {
                'dispatch_type' : fields.selection([('deliver','Deliver'),('collect','Collect'),('Courier','courier')],'Dispatch Type'),
                'balance_of_unpaid': fields.function(_amount_get_balance,  type='float',digits_compute= dp.get_precision('Account'), string='Previous Balance'),
                'balance_of_unpaid_supplier': fields.function(_amount_get_balance_supplier,  type='float',digits_compute= dp.get_precision('Account'), string='Previous Balance'),

                }
    
class account_invoice_line(osv.osv):
    
    _inherit = "account.invoice.line"
    
    @api.one
    @api.depends('price_unit', 'discount', 'invoice_line_tax_id', 'quantity',
        'product_id', 'invoice_id.partner_id', 'invoice_id.currency_id','m2')
    def _compute_price(self):
        price = self.price_unit * (1 - (self.discount or 0.0) / 100.0)
        quantity = self.m2 * self.quantity
        taxes = self.invoice_line_tax_id.compute_all(price, quantity, product=self.product_id, partner=self.invoice_id.partner_id)
        self.price_subtotal = taxes['total']
        if self.invoice_id:
            self.price_subtotal = self.invoice_id.currency_id.round(self.price_subtotal)
    
    def _get_m2(self,cr,uid,ids,field,arg,context=None):
        res = {}
        print ids
        for record in self.browse(cr,uid,ids):
            if record.width == 0.00 or record.height == 0.00:
                res[record.id] = 1.00
            else:
                res[record.id] = (record.width * record.height) / 1000000
        return res
    
    def _get_net_price(self,cr,uid,ids,field,arg,context=None):
        res = {}
        print ids
        for record in self.browse(cr,uid,ids):
            if record.width == 0.00 or record.height == 0.00:
                res[record.id] = record.price_unit * record.quantity
            else:
                res[record.id] = ((record.width * record.height) / 1000000) * record.price_unit * record.quantity
        return res
            
        return res
    
    _columns = {
                'width':fields.float('Width', required='True'),
                'height': fields.float('Height', required='True'),
                'm2' : fields.function(_get_m2,type='float',string='M2'),
                'net_price':fields.function(_get_net_price, type="float", string="Net Price"),
                }
    
    _defaults = {
                 'width' : 0.0,
                 'height' : 0.0,
                 }
    
class account_invoice_tax(osv.osv):
    
    _inherit = "account.invoice.tax"
    
    @api.v8
    def compute(self, invoice):
        tax_grouped = {}
        currency = invoice.currency_id.with_context(date=invoice.date_invoice)
        company_currency = invoice.company_id.currency_id
        for line in invoice.invoice_line:
            taxes = line.invoice_line_tax_id.compute_all(
                (line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                line.quantity * line.m2, line.product_id, invoice.partner_id)['taxes']
            for tax in taxes:
                val = {
                    'invoice_id': invoice.id,
                    'name': tax['name'],
                    'amount': tax['amount'],
                    'manual': False,
                    'sequence': tax['sequence'],
                    'base': currency.round(tax['price_unit'] * line['quantity']),
                }
                if invoice.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = currency.compute(val['base'] * tax['ref_base_sign'], company_currency, round=False)
                    val['tax_amount'] = currency.compute(val['amount'] * tax['ref_tax_sign'], company_currency, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                # If the taxes generate moves on the same financial account as the invoice line
                # and no default analytic account is defined at the tax level, propagate the
                # analytic account from the invoice line to the tax line. This is necessary
                # in situations were (part of) the taxes cannot be reclaimed,
                # to ensure the tax move is allocated to the proper analytic account.
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = currency.round(t['base'])
            t['amount'] = currency.round(t['amount'])
            t['base_amount'] = currency.round(t['base_amount'])
            t['tax_amount'] = currency.round(t['tax_amount'])

        return tax_grouped
    
    
    
