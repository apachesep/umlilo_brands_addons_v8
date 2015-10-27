from openerp.osv import osv, fields

class res_partner(osv.osv):
    
    _inherit = "res.company"
    
    _columns = {
        'vat_registration_no' : fields.char('VAT Registration No.'),
    }
