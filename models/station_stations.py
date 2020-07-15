from odoo import models, fields, api


class ServiceStation(models.Model):
    _name = 'station.stations'
    _inherit = ['mail.activity.mixin']
    _description = 'Add a station, configure their pumps and nozzles.'
    _rec_name = 'name'

    name = fields.Char(string='Station Name')
    manager = fields.Many2one('res.users', string='Manager')
    sales_mode_id = fields.Selection(string='Mode Of Sales', selection=[
        ('metres', 'Metres'), ('litres', 'Litres')], default="metres")
    pump_line = fields.One2many(
        'station.pump', 'station_id', string='Pump Line')


class StationPump(models.Model):
    _name = 'station.pump'
    _inherit = ['mail.activity.mixin']
    _description = 'Create And Manage a pump'
    _rec_name = 'name'

    @api.depends('is_active')
    def set_status(self):
        for rec in self:
            if rec.is_active is True:
                rec.status = 'active'
            elif rec.is_active is False:
                rec.status = 'down'

    name = fields.Char(string='Pump Label', required=True)
    status = fields.Selection([('active', 'Active'), ('down', 'Under Maintenance')],
                              string='Status', compute='set_status', readonly=True)
    station_id = fields.Many2one('station.stations', string='Station Id')
    nozzle_line = fields.One2many(
        'station.nozzles', 'pump_id', string='Nozzle Line')
    is_active = fields.Boolean(string='Is Active', required=True, default=True)


class StationNozzles(models.Model):
    _name = 'station.nozzles'
    _description = 'Manage and support configurations for pump nozzles'
    _rec_name = 'name'

    # name = fields.Char(string='Nozzle Label', required=True)
    name = fields.Many2one('product.product', string='Nozzle Label',
                           domain=[('wet_product', '=', True)])
    inherited_id = fields.Integer(string='Id', related='name.id')

    price = fields.Float(string='Price', related='name.list_price')
    current_reading = fields.Float(string='Current Readings', store=True)

    pump_id = fields.Many2one('station.pump', string='Pump Id')


class StationCsa(models.Model):
    _name = 'station.csa'
    _description = 'Manage station employees.'

    def create_employee(self):
        vals = {
            'name': self.name,
            'work_email': self.email,
            'mobile_phone': self.phone,
            'job_title': 'CSA'
        }
        self.env['hr.employee'].sudo().create(vals)

    def create_payout(self):
        for record in self:
            lines = [(0, 0, {
                'date': rec.date,
                'description': rec.description,
                'amount': rec.amount,
                'reconciled': 'Reconciled'
            }) for rec in record.short_line]
            record.history_line = lines
            record.short_line = [(5, 0, 0)]

    name = fields.Char(string='Name', required=True)
    job_title = fields.Char(string='Job Title', default='CSA', readonly=True)
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    id_number = fields.Char(string='Id Number')
    station_id = fields.Many2one(
        'station.stations', string='Station', required=True)
    short_line = fields.One2many(
        'csa.short.line', 'csa_id', string='Short Line')
    history_line = fields.One2many(
        'csa.history.line', 'csa_id', string='Histpry Line')


class CSAShorts(models.Model):
    _name = 'csa.short.line'
    _description = 'Record CSA shorts and excesses'
    _rec_name = 'csa_id'

    date = fields.Date(string='Date')
    description = fields.Selection([
        ('short', 'Short'),
        ('excess', 'Excess')
    ], string='Description', required=True)
    amount = fields.Float(string='Amount')
    csa_id = fields.Many2one('station.csa', string='CSA Id')


class CsaShortsHistory(models.Model):
    _name = 'csa.history.line'
    _description = 'Keep track of all CSA short or excess that has been cleared'

    date = fields.Date(string='Date', readonly=True)
    description = fields.Selection([
        ('short', 'Short'),
        ('excess', 'Excess')
    ], string='Description', required=True, readonly=True)
    reconciled = fields.Char(string='Reconciled', readonly=True)
    amount = fields.Float(string='Amount', readonly=True)
    csa_id = fields.Many2one('station.csa', string='CSA Id')


class StationSettings(models.Model):
    _name = 'station.settings'
    _description = 'Manage the different settings for all the stations.'
