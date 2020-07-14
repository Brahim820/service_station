from odoo import models, fields


class MpesaRecords(models.Model):
    _name = 'station.mpesa.records'
    _description = 'Get Mpesa Records from SMSSync'
    _rec_name = 'date'

    sender_from = fields.Char(string='From', required=True)
    amount = fields.Float(string='Amount')
    date = fields.Date(string='Date')
    message = fields.Text(string='Message')
    message_id = fields.Char(string='Message Id')
