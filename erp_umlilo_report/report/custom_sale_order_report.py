# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today BrowseInfo (<http://www.browseinfo.in>).
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

import time
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.report import report_sxw
from datetime import datetime

class custom_sale_order(report_sxw.rml_parse):


    def __init__(self, cr, uid, name, context=None):
        super(custom_sale_order, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_date': self._get_date,
            'get_qty_format': self._get_qty_format,
            'get_width' : self._get_width,
            'get_height' : self._get_height,
            })
            
    def _get_width(self, line):
        width1=str(line.width)
        width=width1.split('.')
        return width[0]

    def _get_height(self, line):
        height1=str(line.height)
        height=height1.split('.')
        return height[0]
        

    def _get_date(self, date_order):
        if date_order:
            d = datetime.strptime(date_order, '%Y-%m-%d %H:%M:%S')
            date1 = d.strftime('%d %B %Y')
            return date1

    def _get_qty_format(self, line):
        qty1=str(line.product_uom_qty)
        qty=qty1.split('.')
        return qty[0]


class test_report_template_id_new(osv.AbstractModel):
    _name = 'report.erp_umlilo_report.custom_sale_order_template_id'
    _inherit = 'report.abstract_report'
    _template = 'erp_umlilo_report.custom_sale_order_template_id'
    _wrapped_report_class = custom_sale_order

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
