from odoo import api, fields, models


class StationSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    name = fields.Char(string='Name')
