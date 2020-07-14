from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class Miscelleneous(models.Model):
    _name = 'station.misc'
    _description = 'Record Station Miscelleneous Data'
    _rec_name = 'seq'
    _order = 'seq'

    seq = fields.Char(string='Reference', index=True, copy=False,
                      readonly=True, default=lambda self: _('New'))
    date = fields.Date(string='Date', required=True)
    shift_id = fields.Selection([
        ('morning', 'Morning'),
        ('night', 'Night')
    ], string='Shift')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('locked', 'Locked')
    ], string='Status', readonly=True, index=True, copy=False, default='draft', track_visibility='onchange')

    pump_id = fields.Many2one('station.pump', string='Pump', required=True)
    station_id = fields.Many2one(
        string='Station', related='pump_id.station_id')

    total_litres = fields.Float(compute='_compute_total_litres')
    master_dip = fields.Float(string='Master Dip')
    nozzle_misc_line = fields.One2many(
        'nozzle.misc', 'nozzle_misc_id', string='Nozzle Misc Line')

    def reset_to_draft(self):
        self.adjust_current_readings()
        self.write({'state': 'draft'})

    def approve_button(self):
        self.adjust_current_readings()
        self.write({'state': 'locked'})

    def adjust_current_readings(self):
        current_reading = 0

        for rec in self.nozzle_misc_line:
            nozzle_id = self.env['station.nozzles'].search(
                [('id', '=', rec.nozzle_id.id)])

            if self.state == 'draft':
                current_reading = nozzle_id.mapped(
                    'current_reading')[0] + rec.litres
            else:
                current_reading = nozzle_id.mapped(
                    'current_reading')[0] - rec.litres

            nozzle_id.update({'current_reading': current_reading})

    @api.model
    def create(self, vals):
        if vals.get('seq', _('New')) == _('New'):
            vals['seq'] = self.env['ir.sequence'].next_by_code(
                'station.misc.seq') or _('New')
        result = super(Miscelleneous, self).create(vals)
        return result

    @api.depends('nozzle_misc_line.litres')
    def _compute_total_litres(self):
        for record in self:
            total_litres = 0
            for line in record.nozzle_misc_line:
                total_litres += line.litres
            record.update({'total_litres': total_litres})
        return total_litres

    @api.onchange('station_id')
    def _onchange_station_id_filter_pump(self):
        for rec in self:
            return {'domain':
                    {'pump_id': [('station_id', '=', rec.pump_id.station_id)]}}


class MiscNozzleLine(models.Model):
    _name = 'nozzle.misc'
    _description = 'Create Nozzle Lines'

    nozzle_id = fields.Many2one(
        'station.nozzles', string='Nozzle', required=True)
    eopen = fields.Float(string='Electric Open')
    eclose = fields.Float(string='Electric Close')
    litres = fields.Float(string='Litres', readonly=True,
                          compute='_compute_ltrs')
    nozzle_misc_id = fields.Many2one(
        comodel_name='station.misc', string='Station Misc Id')

    @api.depends('eclose', 'eopen')
    def _compute_ltrs(self):
        '''Compute the litre amounts for each record line '''
        for line in self:
            litres = line.eclose - line.eopen
            line.update({'litres': litres})

    @api.constrains('litres', 'eopen', 'eclose')
    def check_litres(self):
        for rec in self:
            if rec.litres < 0 or rec.eopen < 0 or rec.eclose < 0:
                raise ValidationError(
                    'Please check that the litres are not negative!')
