# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class StationSales(models.Model):
    _name = 'station.sales'
    _description = 'Manage sales at a service station'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'pump'
    _order = 'id desc'

    # This is a development only test function

    # def test(self):
    #     company_id = self.env.user.company_id
    #     print(company_id.partner_id.name)

    #     for line in self.nozzle_record_line:
    #         product = self.env['product.product'].search(
    #             [('id', '=', line.nozzle_id.inherited_id)])

    #         product_stock = self.env['stock.quant'].search(
    #             [('product_id', '=', product.id)])[0]

    #         if self.sales_mode_id == 'metres':
    #             product_stock.sudo().update({
    #                 'quantity': product_stock.quantity - line.ltrs
    #             })
    #         else:
    #             product_stock.sudo().update({
    #                 'quantity': product_stock.quantity - line.litres
    #             })

    @api.model
    def create(self, vals):
        if vals.get('invoice_ref', _('New') == _('New')):
            vals['invoice_ref'] = self.env['ir.sequence'].next_by_code(
                'station.sales.sequence') or _('New')
        result = super().create(vals)
        return result

    def unlink(self):
        for rec in self:
            if (self.state == 'invoiced') and (self.invoice_ids != []):
                raise UserError(
                    _('You can not delete an invoiced sale, consider archiving the record if you must remove it from the view.'))
        return super().unlink()

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

    def _declare_payment_lines(self):
        return ['visa_line', 'loyalty_cards_line',
                'invoices_line', 'shell_pos_line', 'mpesa_line', 'drop_line']

    def prepare_invoice_lines(self):
        invoice_val_dicts = []
        payment_lines = self._declare_payment_lines()
        company_partner_id = self.env.user.company_id.partner_id

        for record in payment_lines:
            for rec in self[record]:
                if rec.amount > 0:
                    invoice_val_list = self._prepare_invoice()
                    invoice_val_list['partner_id'] = rec.partner_id and rec.partner_id.id or company_partner_id.id,
                    invoice_val_list['invoice_partner_bank_id'] = rec.partner_id and rec.partner_id.bank_ids[:1].id \
                        or company_partner_id.bank_ids[:1].id,
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

        if len(new_invoice_vals) == 0:
            raise ValidationError(
                "There is no invoicable line or the line amount, oftenly in the Cash Drop is equals to zero!")
        else:
            for record in new_invoice_vals:
                self.env['account.move'].sudo().create(dict(record))

            self.link_short_or_excess_to_csa()
            self.adjust_inventory()

            self.write({'state': 'invoiced'})

    def link_short_or_excess_to_csa(self):
        '''Shorts or excess should be pushed to the csa's account for accountability or rewarding scheme'''

        for rec in self.env['station.csa'].search([]):
            lines = []
            vals = {
                'date': self.date,
                'description': 'short' if self.short_or_excess < 0 else 'excess',
                'amount': self.short_or_excess,
            }
            lines.append((0, 0, vals))
            rec.short_line = lines if self.csa_id.id == rec.id else None

    def get_invoices_count(self):
        invoices = self.env['account.move'].search(
            [('ref', '=', self.invoice_ref)])
        self.invoices_count = len(invoices)
        self.invoice_ids = invoices

    def action_view_invoice(self):
        invoices = self.mapped('invoice_ids')
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref('account.view_move_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + \
                    [(state, view)
                     for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = invoices.id
        else:
            action = {'type': 'ir.actions.act_window_close'}

        context = {
            'default_type': 'out_invoice',
        }
        return action

    def reset_to_draft(self):
        self.write({'state': 'draft'})

    @ api.constrains('fuel_sales', 'date')
    def approve_fuel_Sales(self):
        for rec in self:
            if rec.date.strftime('%Y-%m-%d') > fields.Datetime.now().strftime('%Y-%m-%d'):
                raise ValidationError(
                    'You cannot approve sales for a future date')

        for rec in self.nozzle_record_line:
            for record in self.env['station.nozzles'].search([]):
                record.write({'current_reading': rec.eclose}
                             ) if record.id == rec.nozzle_id.id else None

        if (self.fuel_sales == 0):
            raise ValidationError('You cannot approve zero sales!')
        else:
            self.write({'state': 'approved'})

    @ api.depends('nozzle_record_line.amount')
    def _compute_fuel_sales(self):
        for record in self:
            fuel_sales = 0
            for line in record.nozzle_record_line:
                fuel_sales += line.amount
            record.update({'fuel_sales': fuel_sales})
        return fuel_sales

    @api.model
    def adjust_inventory(self):
        for line in self.nozzle_record_line:
            product = self.env['product.product'].search(
                [('id', '=', line.nozzle_id.inherited_id)])

            product_stock = self.env['stock.quant'].search(
                [('product_id', '=', product.id)])[0]

            if self.sales_mode_id == 'metres':
                product_stock.sudo().update({
                    'quantity': product_stock.quantity - line.ltrs
                })
            else:
                product_stock.sudo().update({
                    'quantity': product_stock.quantity - line.litres
                })

    def do_taxes(self):
        total_tax = 0
        for line in self.nozzle_record_line:
            product = self.env['product.product'].search(
                [('id', '=', line.nozzle_id.inherited_id)])

            tax_ids = product.mapped(('taxes_id')).id

            tax_percentage = self.env['account.tax'].search(
                [('id', '=', tax_ids)]).mapped('amount')[0]

            taxable_amount = product.mapped('taxable_amount')[0]

            total_tax += (tax_percentage/100) * (taxable_amount * line.amount)

        return total_tax

    @ api.depends('amount_untaxed', 'amount_tax', 'visa_line.amount', 'shell_pos_line.amount',
                  'loyalty_cards_line.amount', 'mpesa_line.amount', 'drop_line.amount',
                  'invoices_line.amount')
    def _compute_total_amount(self):
        # payment_lines = self._declare_payment_lines()
        # payment_totals = ['visa_total', 'shell_pos_total', 'mpesa_total','loyalty_cards_total','invoices_total','drop_total']

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

            # for rec in payment_lines:
            #     for line in record[rec]:

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
            amount_tax = self.do_taxes()

            short_or_excess_display = '{:+}'.format(short_or_excess)

            record.update({
                'visa_total': visa_total,
                'shell_pos_total': shell_pos_total,
                'loyalty_cards_total': loyalty_cards_total,
                'mpesa_total': mpesa_total,
                'invoices_total': invoices_total,
                'drop_total': drop_total,
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
                'total_credits': total_credits,
                'cash_required': cash_required,
                'short_or_excess': short_or_excess,
                'short_or_excess_display': short_or_excess_display,
            })

    @ api.onchange('pump')
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

    @ api.onchange('csa_id')
    def _onchange_csa_id_filter_pump(self):
        for rec in self:
            return {'domain':
                    {'pump': ['&', ('station_id', '=', rec.csa_id.station_id.id), ('is_active', '=', True)]}}

    @ api.onchange('csa_id')
    def _onchange_csa_id_update_dropby(self):
        for rec in self:
            # THIS WILL CLEAR LINES INCASE CSA CHANGES, OTHERWISE IT WILL ADD NEW CSA TO NEXT LINE
            lines = [(5, 0, 0)]
            rec.station_id = self.csa_id.station_id
            rec.sales_mode_id = self.station_id.sales_mode_id
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
    amount_tax = fields.Monetary(string='Tax Amount', readonly=True)
    currency_id = fields.Many2one('res.currency')
    amount_total = fields.Monetary(
        string='Total Amount', readonly=True)
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
    sales_mode_id = fields.Selection(string='Choice', selection=[
        ('metres', 'Metres'), ('litres', 'Litres')])

    invoice_ids = fields.Many2many(
        "account.move", string='Invoices', compute="get_invoices_count", readonly=True, copy=False)
