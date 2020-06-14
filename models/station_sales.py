# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StationSales(models.Model):
    _name = 'station.sales'
    _description = 'Manage sales at a service station'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'pump'
    _order = 'id desc'

    @api.model
    def create(self, vals):
        if vals.get('invoice_ref', _('New') == _('New')):
            vals['invoice_ref'] = self.env['ir.sequence'].next_by_code(
                'station.sales.sequence') or _('New')
        result = super().create(vals)
        return result

    def _prepare_invoice(self):
        journal = self.env['account.move'].with_context(
            default_type='out_invoice')._get_default_journal()

        invoice_vals = {
            'type': 'out_invoice',
            'ref': self.invoice_ref,
            'invoice_user_id': self.csa_id.id,
            'journal_id': journal.id,
            'state': 'draft',
            'invoice_date': self.date,
            'invoice_line_ids': []
        }
        return invoice_vals

    def prepare_invoice_lines(self):
        invoice_val_dicts = []
        payment_lines = ['visa_line', 'loyalty_cards_line', 'invoices_line',
                         'shell_pos_line', 'mpesa_line', 'drop_line']
        invoice_val_dicts = []

        for record in payment_lines:
            if record == 'drop_line':
                me_id = self.env['res.partner'].search([('me_id', '=', True)])
                for rec in self[record]:
                    invoice_val_list = self._prepare_invoice()
                    invoice_val_list['partner_id'] = me_id.id
                    invoice_val_list['invoice_partner_bank_id'] = me_id.bank_ids[:1].id,
                    invoice_val_list['invoice_line_ids'] = [0, 0, {
                        'name': rec.code,
                        'account_id': 1,
                        'quantity': 1,
                        'price_unit': rec.amount,
                    }]
                    invoice_val_dicts.append(invoice_val_list)
            else:
                for rec in self[record]:
                    invoice_val_list = self._prepare_invoice()
                    invoice_val_list['partner_id'] = rec.partner_id.id
                    invoice_val_list['invoice_partner_bank_id'] = rec.partner_id.bank_ids[:1].id,
                    invoice_val_list['invoice_line_ids'] = [0, 0, {
                        'name': rec.code,
                        'account_id': 1,
                        'quantity': 1,
                        'price_unit': rec.amount,
                    }]
                    invoice_val_dicts.append(invoice_val_list)

        return invoice_val_dicts

    def generate_sale_invoices(self):
        new_invoice_vals = self.prepare_invoice_lines()
        for record in new_invoice_vals:
            self.env['account.move'].sudo().create(dict(record))

        self.write({'state': 'invoiced'})

    def open_station_invoices(self):
        return {
            'name': _('Invoices'),
            'domain': [('ref', '=', self.invoice_ref)],
            'view_type': 'form',
            'res.model': 'station.csa',
            'view_id': False,
            'view_mode': 'tree,form',
            'type': 'ir.actions.act_window'
        }

    def get_invoices_count(self):
        count = self.env['account.move'].search_count(
            [('ref', '=', self.invoice_ref)])
        self.invoices_count = count

    def reset_to_draft(self):
        self.write({'state': 'draft'})

    @api.constrains('fuel_sales')
    def approve_fuel_Sales(self):
        for rec in self.nozzle_record_line:
            for record in self.env['station.nozzles'].search([]):
                record.write({'current_reading': rec.eclose}
                             ) if record.id == rec.nozzle_id.id else None
        if (self.fuel_sales == 0):
            raise ValidationError('You cannot approve zero sales!')
        else:
            self.write({'state': 'approved'})

    @api.depends('nozzle_record_line.amount')
    def _compute_fuel_sales(self):
        for record in self:
            fuel_sales = 0
            for line in record.nozzle_record_line:
                fuel_sales += line.amount
            record.update({'fuel_sales': fuel_sales})
        return fuel_sales

    @api.depends('amount_tax', 'amount_untaxed')
    def _compute_taxes(self):
        for rec in self:
            amount = rec.amount_untaxed + \
                (rec.amount_tax/100 * rec.amount_untaxed)
            rec.update({'amount_total': amount})

    @api.depends('amount_untaxed', 'amount_tax', 'visa_line.amount', 'shell_pos_line.amount',
                 'loyalty_cards_line.amount', 'mpesa_line.amount', 'drop_line.amount',
                 'invoices_line.amount')
    def _compute_total_amount(self):
        for record in self:
            visa_total = 0.0
            shell_pos_total = 0.0
            mpesa_total = 0.0
            loyalty_cards_total = 0.0
            invoices_total = 0.0
            drop_total = 0.0
            fuel_sales = record.fuel_sales
            total_credits = 0.0
            cash_required = 0.0
            short_or_excess = 0.0

            for line in record.visa_line:
                visa_total += line.amount

            for line in record.shell_pos_line:
                shell_pos_total += line.amount

            for line in record.mpesa_line:
                mpesa_total += line.amount

            for line in record.loyalty_cards_line:
                loyalty_cards_total += line.amount

            for line in record.invoices_line:
                invoices_total += line.amount

            for line in record.drop_line:
                drop_total += line.amount

            total_credits = visa_total + invoices_total + \
                mpesa_total + shell_pos_total + loyalty_cards_total
            cash_required = fuel_sales - total_credits
            short_or_excess = drop_total - cash_required
            amount_untaxed = total_credits + drop_total

            short_or_excess_display = '{:+}'.format(short_or_excess)

            record.update({
                'visa_total': visa_total,
                'shell_pos_total': shell_pos_total,
                'loyalty_cards_total': loyalty_cards_total,
                'mpesa_total': mpesa_total,
                'invoices_total': invoices_total,
                'drop_total': drop_total,
                'amount_untaxed': amount_untaxed,
                'total_credits': total_credits,
                'cash_required': cash_required,
                'short_or_excess': short_or_excess,
                'short_or_excess_display': short_or_excess_display,
            })

    @api.onchange('pump')
    def _onchange_pump_create_nozzles(self):
        for rec in self:
            lines = [(5, 0, 0)]
            for nozzle in self.pump.nozzle_line:
                val = {
                    'nozzle_id': nozzle,
                    'price': nozzle.price,
                    'eopen': nozzle['current_reading']
                }
                lines.append((0, 0, val))
            rec.nozzle_record_line = lines

    @api.onchange('csa_id')
    def _onchange_csa_id_filter_pump(self):
        for rec in self:
            return {'domain':
                    {'pump': [('station_id', '=', rec.csa_id.station_id.id)]}}

    @api.onchange('csa_id')
    def _onchange_csa_id_update_dropby(self):
        for rec in self:
            lines = [(5, 0, 0)]
            for line in self.csa_id:
                rec.station_id = self.csa_id.station_id
                val = {
                    'code': '0000',
                    'drop_by': self.csa_id
                }
                lines.append((0, 0, val))
            rec.drop_line = lines

    station_id = fields.Many2one(
        'station.stations', string='Station')
    csa_id = fields.Many2one('station.csa', string='CSA', required=True)
    pump = fields.Many2one('station.pump', string='Pump', required=True)
    date = fields.Date(
        string='Date', default=fields.Datetime.now, required=True)
    amount_untaxed = fields.Monetary(string='Untaxed Amount', readonly=True)
    amount_tax = fields.Monetary(string='Tax Amount')
    currency_id = fields.Many2one('res.currency')
    amount_total = fields.Monetary(
        string='Total Amount', compute='_compute_taxes', readonly=True)
    fuel_sales = fields.Monetary(string='Fuel Sales', track_visibility='onchange',
                                 compute='_compute_fuel_sales')
    total_credits = fields.Monetary(string='Total Credits', readonly=True)
    cash_required = fields.Monetary(
        string='Cash Required', track_visibility='onchange', readonly=True)
    short_or_excess = fields.Monetary(string='Short/ Excess', readonly=True)
    short_or_excess_display = fields.Char(
        string='Short/ Excess', readonly=True)

    visa_line = fields.One2many('visa.line', 'visa_id', string='Visa Line')
    shell_pos_line = fields.One2many(
        'shell.pos.line', 'shell_pos_id', string='Shell Pos Line')
    loyalty_cards_line = fields.One2many(
        'loyalty.cards.line', 'loyalty_cards_id', string='Loyalty Cards Line')
    mpesa_line = fields.One2many('mpesa.line', 'mpesa_id', string='Mpesa Line')
    invoices_line = fields.One2many(
        'invoices.line', 'invoices_id', string='Invoices Line')
    drop_line = fields.One2many('drop.line', 'drop_id', string='Drop Line')
    nozzle_record_line = fields.One2many(
        'nozzle.record.line', 'nozzle_record_id', string='Nozzle Record Line')
    visa_total = fields.Monetary(string='Visa Total', compute='_compute_total_amount',
                                 track_visibility='onchange', store=True, readonly=True)
    shell_pos_total = fields.Monetary(
        string='Shell Pos Total', compute='_compute_total_amount', readonly=True, store=True)
    loyalty_cards_total = fields.Monetary(
        string='Loyalty Cards Total', compute='_compute_total_amount', readonly=True, store=True)
    mpesa_total = fields.Monetary(
        string='Mpesa Total', compute='_compute_total_amount', readonly=True, store=True)
    invoices_total = fields.Monetary(
        string='Invoices Total', compute='_compute_total_amount', readonly=True, store=True)
    drop_total = fields.Monetary(
        string='Cash Drop Total', compute='_compute_total_amount', readonly=True, store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'To Be Invoiced'),
        ('invoiced', 'Invoiced'),
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')
    shift_id = fields.Selection(
        [('morning', 'Morning'), ('night', 'Night')], string='Shift', required=True)
    invoices_count = fields.Integer(
        string='Invoices', compute="get_invoices_count")
    invoice_ref = fields.Char(string='Ref')

    # company_id = fields.Many2one(
    #     'res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    # payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', check_company=True,
    #                                   domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    # pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', check_company=True,
    #                                readonly=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    # currency_id = fields.Many2one(
    #     "res.currency", related='pricelist_id.currency_id', string="Currency", readonly=True, required=True)
    # analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account', readonly=True, copy=False,
    #                                       check_company=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    # choices = fields.Selection(string='Choice', selection=[
    #                           ('metres', 'Metres'), ('litres', 'Litres'), ])

    # transaction_ids = fields.Many2many('payment.transaction', 'sale_order_transaction_rel', 'sale_order_id', 'transaction_id',
    #                                    string='Transactions', copy=False, readonly=True)
    # authorized_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_authorized_transaction_ids',
    #                                               string='Authorized Transactions', copy=False, readonly=True)

    # @api.depends('transaction_ids')
    # def _compute_authorized_transaction_ids(self):
    #     for trans in self:
    #         trans.authorized_transaction_ids = trans.transaction_ids.filtered(
    #             lambda t: t.state == 'authorized')
