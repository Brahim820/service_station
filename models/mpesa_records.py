from odoo import models, fields, api
from odoo.exceptions import ValidationError


class MpesaRecords(models.Model):
    _name = 'station.mpesa.records'
    _description = 'Get Mpesa Records from SMSSync'
    _rec_name = 'code'

    sender_from = fields.Char(string='From', required=True)
    amount = fields.Float(string='Amount')
    date = fields.Date(string='Date')
    message = fields.Text(string='Message')
    message_id = fields.Char(string='Message Id')
    code = fields.Char(string='Code', required=True)
    assigned = fields.Boolean(string='Assigned', readonly=True)

    @api.constrains('code')
    def check_unique_code(self):
        codes = self.search([('code', '=', self.code)])
        if len(codes) > 1:
            raise ValidationError('Mpesa Code has to be Unique!')

    def copy(self, default=None):
        default = dict(default or {})

        copied_count = self.search_count(
            [('code', '=like', u"Copy of {}%".format(self.code))])
        if not copied_count:
            new_code = u"Copy of {}".format(self.code)
        else:
            new_code = u"Copy of {} ({})".format(self.code, copied_count)

        default['code'] = new_code
        return super().copy(default)
