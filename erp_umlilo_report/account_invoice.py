import itertools
from lxml import etree

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp


class account_invoice(models.Model):
    
    _inherit = "account.invoice"
    
    
    dispatch_type = fields.Selection([('deliver','Deliver'), ('collect','Collect'), ('courier','Courier')], string='Status', index=True)
    x_job_number = fields.Char('Job Number', size=5)
    customer_po_no = fields.Char('Customer PO No', size=10)
    
    @api.multi
    def invoice_print(self):
        '''
        This function prints the sales order and mark it as sent, so that we can see more easily the next step of the workflow
        '''
        assert len(self) == 1, 'This option should only be used for a single id at a time.'
        self.sent = True
        return self.env['report'].get_action(self, 'erp_umlilo_report.custom_invoice_report_template_id')

    @api.model
    def _prepare_refund(self, invoice, date=None, period_id=None, description=None, journal_id=None):
        """ Prepare the dict of values to create the new refund from the invoice.
            This method may be overridden to implement custom
            refund generation (making sure to call super() to establish
            a clean extension chain).

            :param record invoice: invoice to refund
            :param string date: refund creation date from the wizard
            :param integer period_id: force account.period from the wizard
            :param string description: description of the refund from the wizard
            :param integer journal_id: account.journal from the wizard
            :return: dict of value to create() the refund
        """
        values = {}
        values = super(account_invoice, self)._prepare_refund(invoice, date=None, period_id=None, description=None, journal_id=None)
        values['x_job_number'] = invoice['x_job_number'] or False
        print '\n in prepare refund of custom',values
        return values
