from openerp.osv import osv, fields
from datetime import datetime, timedelta
import time
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import api
from openerp.osv import fields, osv, orm
from openerp.tools import float_compare
from openerp.tools.translate import _
from openerp import tools, SUPERUSER_ID
from openerp.addons.product import _common

class purchase_order(osv.osv):
    
    _inherit = "purchase.order"
    
    _columns = {
                'dispatch_type' : fields.selection([('deliver','Deliver'),('collect','Collect'),('Courier','courier')],'Dispatch Type'),
                }


class purchase_order_line(osv.osv):

    _inherit = "purchase.order.line"

    def _get_squaremeter(self,cr,uid,ids,field,arg,context=None):
        res = {}
        for record in self.browse(cr,uid,ids):
            if record.width == 0.00 or record.height == 0.00:
                res[record.id] = 1.00
            else:
                res[record.id] = (record.width * record.height) / 1000000
        return res

    _columns = {
                'width':fields.float('Width', required='True'),
                'height': fields.float('Height', required='True'),
                'square_meter' : fields.function(_get_squaremeter,type='float',string='M2'),
                }

    _defaults = {
                'width' : 0.0,
                'height' : 0.0,
                 }


class mrp_production(osv.osv):

    _inherit = "mrp.production"

    def _get_squaremeter(self,cr,uid,ids,field,arg,context=None):
        res = {}
        for record in self.browse(cr,uid,ids):
            if record.width == 0.00 or record.height == 0.00:
                res[record.id] = 1.00
            else:
                res[record.id] = (record.width * record.height) / 1000000
        return res

    _columns = {
                'width':fields.float('Width', required='True'),
                'height': fields.float('Height', required='True'),
                'square_meter' : fields.function(_get_squaremeter,type='float',string='M2'),
                }

    _defaults = {
                'width' : 0.0,
                'height' : 0.0,
                 }

    def _make_service_procurement(self, cr, uid, line, context=None):
        prod_obj = self.pool.get('product.product')
        if prod_obj.need_procurement(cr, uid, [line.product_id.id], context=context):
            vals = {
                'name': line.production_id.name,
                'origin': line.production_id.name,
                'company_id': line.production_id.company_id.id,
                'date_planned': line.production_id.date_planned,
                'product_id': line.product_id.id,
                'product_qty': line.product_qty,
                'product_uom': line.product_uom.id,
                'product_uos_qty': line.product_uos_qty,
                'product_uos': line.product_uos.id,
                }
            proc_obj = self.pool.get("procurement.order")
            proc = proc_obj.create(cr, uid, vals, context=context)
            proc_obj.run(cr, uid, [proc], context=context)

    def _make_consume_line_from_data(self, cr, uid, production, product, uom_id, qty, uos_id, uos_qty, context=None):
        stock_move = self.pool.get('stock.move')
        loc_obj = self.pool.get('stock.location')
        # Internal shipment is created for Stockable and Consumer Products
        if product.type not in ('product', 'consu'):
            return False
        # Take routing location as a Source Location.
        source_location_id = production.location_src_id.id
        prod_location_id = source_location_id
        prev_move= False
        if production.bom_id.routing_id and production.bom_id.routing_id.location_id and production.bom_id.routing_id.location_id.id != source_location_id:
            source_location_id = production.bom_id.routing_id.location_id.id
            prev_move = True

        destination_location_id = production.product_id.property_stock_production.id
        move_id = stock_move.create(cr, uid, {
            'name': production.name,
            'date': production.date_planned,
            'product_id': product.id,
            'product_uom_qty': qty,
            'product_uom': uom_id,
            'product_uos_qty': uos_id and uos_qty or False,
            'product_uos': uos_id or False,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'company_id': production.company_id.id,
            'procure_method': prev_move and 'make_to_stock' or self._get_raw_material_procure_method(cr, uid, product, context=context), #Make_to_stock avoids creating procurement
            'raw_material_production_id': production.id,
            #this saves us a browse in create()
            'price_unit': product.standard_price,
            'origin': production.name,
            'warehouse_id': loc_obj.get_warehouse(cr, uid, production.location_src_id, context=context),
            'group_id': production.move_prod_id.group_id.id,
        }, context=context)

        if prev_move:
            prev_move = self._create_previous_move(cr, uid, move_id, product, prod_location_id, source_location_id, context=context)
            stock_move.action_confirm(cr, uid, [prev_move], context=context)
        return move_id

    def _make_production_consume_line(self, cr, uid, line, context=None):
        return self._make_consume_line_from_data(cr, uid, line.production_id, line.product_id, line.product_uom.id, line.product_qty, line.product_uos.id, line.product_uos_qty, context=context)

    def _make_production_produce_line(self, cr, uid, production, context=None):
        stock_move = self.pool.get('stock.move')
        proc_obj = self.pool.get('procurement.order')
        source_location_id = production.product_id.property_stock_production.id
        destination_location_id = production.location_dest_id.id
        procs = proc_obj.search(cr, uid, [('production_id', '=', production.id)], context=context)
        procurement = procs and\
            proc_obj.browse(cr, uid, procs[0], context=context) or False
        data = {
            'name': production.name,
            'date': production.date_planned,
            'product_id': production.product_id.id,
            'product_uom': production.product_uom.id,
            'product_uom_qty': production.product_qty,
            'product_uos_qty': production.product_uos and production.product_uos_qty or False,
            'product_uos': production.product_uos and production.product_uos.id or False,
            'location_id': source_location_id,
            'location_dest_id': destination_location_id,
            'move_dest_id': production.move_prod_id.id,
            'procurement_id': procurement and procurement.id,
            'company_id': production.company_id.id,
            'production_id': production.id,
            'origin': production.name,
            'group_id': procurement and procurement.group_id.id,
        }
        move_id = stock_move.create(cr, uid, data, context=context)
        #a phantom bom cannot be used in mrp order so it's ok to assume the list returned by action_confirm
        #is 1 element long, so we can take the first.
        return stock_move.action_confirm(cr, uid, [move_id], context=context)[0]





    def _action_compute_lines(self, cr, uid, ids, properties=None, context=None):
        if properties is None:
            properties = []
        results = []
        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        for production in self.browse(cr, uid, ids, context=context):
            #unlink product_lines
            prod_line_obj.unlink(cr, SUPERUSER_ID, [line.id for line in production.product_lines], context=context)
            #unlink workcenter_lines
            workcenter_line_obj.unlink(cr, SUPERUSER_ID, [line.id for line in production.workcenter_lines], context=context)
            # search BoM structure and route
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = bom_obj._bom_find(cr, uid, product_id=production.product_id.id, properties=properties, context=context)
                if bom_id:
                    bom_point = bom_obj.browse(cr, uid, bom_id)
                    routing_id = bom_point.routing_id.id or False
                    self.write(cr, uid, [production.id], {'bom_id': bom_id, 'routing_id': routing_id})

            if not bom_id:
                raise osv.except_osv(_('Error!'), _("Cannot find a bill of material for this product."))

            # get components and workcenter_lines from BoM structure
            factor = uom_obj._compute_qty(cr, uid, production.product_uom.id, (production.product_qty * production.square_meter), bom_point.product_uom.id)
            # product_lines, workcenter_lines
            results, results2 = bom_obj._bom_explode(cr, uid, bom_point, production.product_id, factor / bom_point.product_qty, properties, routing_id=production.routing_id.id, context=context)

            # reset product_lines in production order
            for line in results:
                line['production_id'] = production.id
                prod_line_obj.create(cr, uid, line)

            #reset workcenter_lines in production order
            for line in results2:
                line['production_id'] = production.id
                workcenter_line_obj.create(cr, uid, line)
        return results

    def action_compute(self, cr, uid, ids, properties=None, context=None):
        return len(self._action_compute_lines(cr, uid, ids, properties=properties, context=context))


    def action_confirm(self, cr, uid, ids, context=None):
        uncompute_ids = filter(lambda x: x, [not x.product_lines and x.id or False for x in self.browse(cr, uid, ids, context=context)])
        self.action_compute(cr, uid, uncompute_ids, context=context)
        for production in self.browse(cr, uid, ids, context=context):
            self._make_production_produce_line(cr, uid, production, context=context)

            stock_moves = []
            for line in production.product_lines:
                if line.product_id.type != 'service':
                    stock_move_id = self._make_production_consume_line(cr, uid, line, context=context)
                    stock_moves.append(stock_move_id)
                else:
                    self._make_service_procurement(cr, uid, line, context=context)
            if stock_moves:
                self.pool.get('stock.move').action_confirm(cr, uid, stock_moves, context=context)
            production.write({'state': 'confirmed'})
        return 0

class sale_order(osv.Model):
    _inherit = 'sale.order'

    def _prepare_order_line_procurement(self, cr, uid, order, line, group_id=False, context=None):
        result = super(sale_order, self)._prepare_order_line_procurement(cr, uid, order, line, group_id=group_id, context=context)
        result['width'] = line.width
        result['height'] = line.height
        result['property_ids'] = [(6, 0, [x.id for x in line.property_ids])]
        return result

class procurement_order(osv.osv):
    _inherit = 'procurement.order'

    _columns = {
                'width':fields.float('Width'),
                'height': fields.float('Height'),
                }


    def _prepare_mo_vals(self, cr, uid, procurement, context=None):
        res_id = procurement.move_dest_id and procurement.move_dest_id.id or False
        newdate = self._get_date_planned(cr, uid, procurement, context=context)
        bom_obj = self.pool.get('mrp.bom')
        if procurement.bom_id:
            bom_id = procurement.bom_id.id
            routing_id = procurement.bom_id.routing_id.id
        else:
            properties = [x.id for x in procurement.property_ids]
            bom_id = bom_obj._bom_find(cr, uid, product_id=procurement.product_id.id,
                                       properties=properties, context=context)
            bom = bom_obj.browse(cr, uid, bom_id, context=context)
            routing_id = bom.routing_id.id
        return {
            'origin': procurement.origin,
            'product_id': procurement.product_id.id,
            'product_qty': procurement.product_qty,
            'width': procurement.width,
            'height': procurement.height,
            'product_uom': procurement.product_uom.id,
            'product_uos_qty': procurement.product_uos and procurement.product_uos_qty or False,
            'product_uos': procurement.product_uos and procurement.product_uos.id or False,
            'location_src_id': procurement.location_id.id,
            'location_dest_id': procurement.location_id.id,
            'bom_id': bom_id,
            'routing_id': routing_id,
            'date_planned': newdate.strftime('%Y-%m-%d %H:%M:%S'),
            'move_prod_id': res_id,
            'company_id': procurement.company_id.id,
        }

    def make_mo(self, cr, uid, ids, context=None):
        res = {}
        production_obj = self.pool.get('mrp.production')
        procurement_obj = self.pool.get('procurement.order')
        for procurement in procurement_obj.browse(cr, uid, ids, context=context):
            if self.check_bom_exists(cr, uid, [procurement.id], context=context):
                #create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
                vals = self._prepare_mo_vals(cr, uid, procurement, context=context)
                produce_id = production_obj.create(cr, SUPERUSER_ID, vals, context=context)
                res[procurement.id] = produce_id
                self.write(cr, uid, [procurement.id], {'production_id': produce_id})
                self.production_order_create_note(cr, uid, procurement, context=context)
                production_obj.action_compute(cr, uid, [produce_id], properties=[x.id for x in procurement.property_ids])
                production_obj.signal_workflow(cr, uid, [produce_id], 'button_confirm')
            else:
                res[procurement.id] = False
                self.message_post(cr, uid, [procurement.id], body=_("No BoM exists for this product!"), context=context)
        return res


    def make_po(self, cr, uid, ids, context=None):
        res = {}
        company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
        po_obj = self.pool.get('purchase.order')
        po_line_obj = self.pool.get('purchase.order.line')
        seq_obj = self.pool.get('ir.sequence')
        pass_ids = []
        linked_po_ids = []
        sum_po_line_ids = []
        for procurement in self.browse(cr, uid, ids, context=context):
            partner = self._get_product_supplier(cr, uid, procurement, context=context)
            if not partner:
                self.message_post(cr, uid, [procurement.id], _('There is no supplier associated to product %s') % (procurement.product_id.name))
                res[procurement.id] = False
            else:
                schedule_date = self._get_purchase_schedule_date(cr, uid, procurement, company, context=context)
                purchase_date = self._get_purchase_order_date(cr, uid, procurement, company, schedule_date, context=context)
                line_vals = self._get_po_line_values_from_proc(cr, uid, procurement, partner, company, schedule_date, context=context)
                print "___________________line_val________________s__________________",line_vals
                #look for any other draft PO for the same supplier, to attach the new line on instead of creating a new draft one
                available_draft_po_ids = po_obj.search(cr, uid, [
                    ('partner_id', '=', partner.id), ('state', '=', 'draft'), ('picking_type_id', '=', procurement.rule_id.picking_type_id.id),
                    ('location_id', '=', procurement.location_id.id), ('company_id', '=', procurement.company_id.id), ('dest_address_id', '=', procurement.partner_dest_id.id)], context=context)
                if available_draft_po_ids:
                    po_id = available_draft_po_ids[0]
                    po_rec = po_obj.browse(cr, uid, po_id, context=context)
                    #if the product has to be ordered earlier those in the existing PO, we replace the purchase date on the order to avoid ordering it too late
                    if datetime.strptime(po_rec.date_order, DEFAULT_SERVER_DATETIME_FORMAT) > purchase_date:
                        po_obj.write(cr, uid, [po_id], {'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
                    #look for any other PO line in the selected PO with same product and UoM to sum quantities instead of creating a new po line
                    available_po_line_ids = po_line_obj.search(cr, uid, [('order_id', '=', po_id), ('product_id', '=', line_vals['product_id']), ('height','=',procurement.height), ('width','=',procurement.width), ('product_uom', '=', line_vals['product_uom'])], context=context)
                    if available_po_line_ids:
                        po_line = po_line_obj.browse(cr, uid, available_po_line_ids[0], context=context)
                        po_line_obj.write(cr, SUPERUSER_ID, po_line.id, {'product_qty': po_line.product_qty + line_vals['product_qty'], 'height': procurement.height, 'width': procurement.width}, context=context)
                        po_line_id = po_line.id
                        sum_po_line_ids.append(procurement.id)
                    else:
                        line_vals.update({'order_id':po_id,'height': procurement.height, 'width': procurement.width})
                        po_line_id = po_line_obj.create(cr, SUPERUSER_ID, line_vals, context=context)
                        linked_po_ids.append(procurement.id)
                else:
                    name = seq_obj.get(cr, uid, 'purchase.order') or _('PO: %s') % procurement.name
                    po_vals = {
                        'name': name,
                        'origin': procurement.origin,
                        'partner_id': partner.id,
                        'location_id': procurement.location_id.id,
                        'picking_type_id': procurement.rule_id.picking_type_id.id,
                        'pricelist_id': partner.property_product_pricelist_purchase.id,
                        'currency_id': partner.property_product_pricelist_purchase and partner.property_product_pricelist_purchase.currency_id.id or procurement.company_id.currency_id.id,
                        'date_order': purchase_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'company_id': procurement.company_id.id,
                        'fiscal_position': partner.property_account_position and partner.property_account_position.id or False,
                        'payment_term_id': partner.property_supplier_payment_term.id or False,
                        'dest_address_id': procurement.partner_dest_id.id,
                    }
                    line_vals.update({'height':procurement.height, 'width':procurement.width})
                    po_id = self.create_procurement_purchase_order(cr, SUPERUSER_ID, procurement, po_vals, line_vals, context=context)
                    po_line_id = po_obj.browse(cr, uid, po_id, context=context).order_line[0].id
                    pass_ids.append(procurement.id)
                res[procurement.id] = po_line_id
                self.write(cr, uid, [procurement.id], {'purchase_line_id': po_line_id}, context=context)
        if pass_ids:
            self.message_post(cr, uid, pass_ids, body=_("Draft Purchase Order created"), context=context)
        if linked_po_ids:
            self.message_post(cr, uid, linked_po_ids, body=_("Purchase line created and linked to an existing Purchase Order"), context=context)
        if sum_po_line_ids:
            self.message_post(cr, uid, sum_po_line_ids, body=_("Quantity added in existing Purchase Order Line"), context=context)
        return res


class stock_move(osv.Model):
    _inherit = 'stock.move'


    def _prepare_procurement_from_move(self, cr, uid, move, context=None):
        origin = (move.group_id and (move.group_id.name + ":") or "") + (move.rule_id and move.rule_id.name or move.origin or "/")
        group_id = move.group_id and move.group_id.id or False
        proc_obj = self.pool.get('procurement.order')
        height = 0.0
        width = 0.0
        group = move.group_id and move.group_id.id or False
        proc_id = proc_obj.search(cr, uid, [('group_id', '=',group)], context=context)
        if proc_id:
            for proc in proc_obj.browse(cr,uid,proc_id,context=context):
                procheight = proc.height or 0.0
                procwidth = proc.width or 0.0
        if move.rule_id:
            if move.rule_id.group_propagation_option == 'fixed' and move.rule_id.group_id:
                group_id = move.rule_id.group_id.id
            elif move.rule_id.group_propagation_option == 'none':
                group_id = False
        return {
            'height': procheight,
            'width': procwidth,
            'name': move.rule_id and move.rule_id.name or "/",
            'origin': origin,
            'company_id': move.company_id and move.company_id.id or False,
            'date_planned': move.date,
            'product_id': move.product_id.id,
            'product_qty': move.product_uom_qty,
            'product_uom': move.product_uom.id,
            'product_uos_qty': (move.product_uos and move.product_uos_qty) or move.product_uom_qty,
            'product_uos': (move.product_uos and move.product_uos.id) or move.product_uom.id,
            'location_id': move.location_id.id,
            'move_dest_id': move.id,
            'group_id': group_id,
            'route_ids': [(4, x.id) for x in move.route_ids],
            'warehouse_id': move.warehouse_id.id or (move.picking_type_id and move.picking_type_id.warehouse_id.id or False),
            'priority': move.priority,
        }