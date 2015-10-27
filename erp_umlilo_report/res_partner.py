import datetime
from lxml import etree
import math
import pytz
import urlparse

import openerp
from openerp import tools, api
from openerp.osv import osv, fields
from openerp.osv.expression import get_unaccent_wrapper
from openerp.tools.translate import _



class res_partner(osv.Model):
	_name = 'res.partner'
	_inherit = 'res.partner'
	
	_columns = {
			'customer_vat_no' : fields.char('Customer VAT No', size=10),
			'customer_code' : fields.char('Customer Code', size=10),
	
	}
