# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class NozzleRecordLine(models.Model):
    _name = 'nozzle.record.line'
    _description = 'Sales from a given pump'

    @api.depends('eclose', 'eopen')
    def _compute_ltrs(self):
        """Compute the litre amounts for each record line """
        for line in self:
            litres = line.eclose - line.eopen
            line.update({'ltrs': litres})

    @api.depends('ltrs', 'price', 'litres')
    def _compute_subtotal(self):
        """Compute the total amounts for each line"""
        for line in self:
            if self.nozzle_record_id.sales_mode_id == 'metres':
                amount = (line.ltrs * line.price)
                line.update({'amount': amount})

            elif self.nozzle_record_id.sales_mode_id == 'litres':
                amount = (line.litres * line.price)
                line.update({'amount': amount})

    @api.constrains('ltrs', 'eopen', 'eclose', 'litres')
    def check_litres(self):
        """Ensure that litres sold in a day are not negative for select type of form"""
        for rec in self:
            if (self.nozzle_record_id.sales_mode_id == 'metres') and (rec.ltrs < 0 or rec.eopen < 0 or rec.eclose < 0):
                raise ValidationError('No negative sales are allowed !')

            elif self.nozzle_record_id.sales_mode_id == 'litres' and rec.litres < 0:
                raise ValidationError('No negative sales are allowed !')

    @api.onchange('mclose')
    def onchange_mclose(self):
        for rec in self:
            rec.update({'eclose': rec.mclose})

    nozzle_id = fields.Many2one(
        string='Nozzle', comodel_name='station.nozzles', required=True,
        domain=[('wet_product', '=', True)])
    mclose = fields.Float(string='Manual Close', digits=(12, 3))
    eclose = fields.Float(string='Elec. Close', digits=(12, 3), store=True)
    eopen = fields.Float(string='Elec. Open')
    ltrs = fields.Float(string='Litres', store=True,
                        compute='_compute_ltrs', digits=(12, 3))
    litres = fields.Float(string='Litres', store=True, digits=(12, 3))
    price = fields.Float(string='Price')
    amount = fields.Float(string='Amount', readonly=True,
                          compute='_compute_subtotal')

    nozzle_record_id = fields.Many2one(
        comodel_name='station.sales', string='Station Sales Id')
    currency_id = fields.Many2one('res.currency')


class VisaLine(models.Model):
    _name = 'visa.line'
    _description = 'Visa Payment Line'

    code = fields.Char(string='Code', required=True)
    amount = fields.Monetary('Amount', 'currency_id')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    currency_id = fields.Many2one('res.currency')
    visa_id = fields.Many2one(comodel_name='station.sales', string='Visa Id')


class ShellPosLine(models.Model):
    _name = 'shell.pos.line'
    _description = 'Shell Pos Payment Line'

    code = fields.Char(string='Code', required=True)
    amount = fields.Monetary('Amount', 'currency_id')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    currency_id = fields.Many2one('res.currency')
    shell_pos_id = fields.Many2one(
        comodel_name='station.sales', string='Shell Pos Id')


class LoyaltyCardLine(models.Model):
    _name = 'loyalty.cards.line'
    _description = 'Loyalty Card Payment Line'

    code = fields.Char(string='Code', required=True)
    amount = fields.Monetary('Amount', 'currency_id')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    currency_id = fields.Many2one('res.currency')
    loyalty_cards_id = fields.Many2one(
        comodel_name='station.sales', string='Loyalty Cards Id')


class MpesaLine(models.Model):
    _name = 'mpesa.line'
    _description = 'Mpesa Payment Line'

    code = fields.Char(string='Code', required=True)
    amount = fields.Monetary('Amount', 'currency_id')
    message = fields.Text(string='Message')
    message_id = fields.Char(string='Message_ID')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    currency_id = fields.Many2one('res.currency')
    mpesa_id = fields.Many2one(
        comodel_name='station.sales', string='Mpesa Id')

    @api.model
    def unlink(self):
        # When a record is deleted from the mpesa lines. It is marked as open to be assigned again.
        for rec in self:
            message = self.env['station.mpesa.records'].search(
                [('message_id', '=', rec.message_id)])
            message.update({
                'assigned': False
            })
        return super().unlink()


class InvoicesLine(models.Model):
    _name = 'invoices.line'
    _description = 'Invoices Payment Line'

    code = fields.Char(string='Code', required=True)
    amount = fields.Monetary('Amount', 'currency_id')
    partner_id = fields.Many2one('res.partner', string='Customer')
    currency_id = fields.Many2one('res.currency')
    invoices_id = fields.Many2one(
        comodel_name='station.sales', string='Invoices Id')


class DropLine(models.Model):
    _name = 'drop.line'
    _description = 'Drop cash at the register'

    code = fields.Char(string='Code', required=True,)
    amount = fields.Monetary('Amount', 'currency_id')
    currency_id = fields.Many2one('res.currency')
    drop_by = fields.Many2one(
        'station.csa', string='Dropped By')
    partner_id = fields.Many2one('res.partner', string='Customer')
    drop_id = fields.Many2one(comodel_name='station.sales', string='Drop Id')
