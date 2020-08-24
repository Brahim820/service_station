from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date


class MpesaRecordsWizard(models.TransientModel):
    _name = 'mpesa.records.wizard'
    _description = 'Get Mpesa Records for a particular date'

    date = fields.Date(string='Date', default=fields.Date.today())
    mpesa_messages = fields.Many2many('station.mpesa.records', string='Mpesa Messages')

    def action_add_mpesa_records(self):
        '''
        Take the selected mpesa messages ad add them into the Mpesa Lines.
        '''
        record = self.env['station.sales'].browse(
            self._context.get('active_ids', []))

        for rec in self.mpesa_messages:
            if rec.assigned == True:
                raise ValidationError(
                    'Remove all records whose assigned value is checked!')

        # record.mpesa_line = [(5, 0, 0)]
        for rec in self.mpesa_messages:
            vals = {
                'code': rec.code,
                'message': rec.message,
                'amount': rec.amount,
                'message_id': rec.message_id
            }

            message = self.env['station.mpesa.records'].search([('message_id', '=', rec.message_id)])
            message.update({'assigned': True})

            record.mpesa_line = [(0, 0, vals)]


class CsaReconciliation(models.TransientModel):
    _name = 'csa.reconciliation'
    _description = 'Handle how Csa shorts and excesses are reconcilled.'

    @api.onchange('amount')
    def get_pending_balance(self):
        self.update({'balance': self.total-self.amount})

    amount = fields.Float(string='Amount', required=True)
    total = fields.Float(string='Total', readonly=True)
    balance = fields.Float(string='Remaining Balance', readonly=True)

    def action_reconcile(self):
        record = self.env['station.csa'].browse(
            self._context.get('active_ids', []))

        record.short_line = [(0, 0, {
            'date': date.today(),
            'description': 'reconcile',
            'amount': self.amount,
        })]