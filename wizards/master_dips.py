from odoo import api, fields, models


class MasterDips(models.TransientModel):
    _name = 'master.dips'
    _description = 'Record master dips and other inaccuracies'

    master_dip = fields.Float(string='Master Dip')
    date = fields.Datetime(string='Time')
    pump_skips = fields.Float(string='Pump Skips')
    empty_run = fields.Float(string='Empty Run', digits=(0, 2))
