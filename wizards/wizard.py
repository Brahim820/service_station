from odoo import api, fields, models
from odoo.exceptions import ValidationError


class MpesaRecordsWizard(models.TransientModel):
    _name = 'mpesa.records.wizard'
    _description = 'Get Mpesa Records for a particular date'

    date = fields.Date(string='Date', default=fields.Datetime.now())
    mpesa_messages = fields.Many2many(
        'station.mpesa.records', string='Mpesa Messages')

    def action_add_mpesa_records(self):
        '''
        Take the selected mpesa messages ad add them into the Mpesa Lines.
        '''
        record = self.env['station.sales'].browse(
            self._context.get('active_ids', []))

        # mpesa_records = self.env['station.mpesa.records'].search(
        #     [("date", "=", self.date.strftime('%Y-%m-%d'))])
        # mpesa_lines = self.env['mpesa.line'].search(
        #     []).mapped('message_id')
        # new_id = self.mpesa_messages.mapped('message_id')

        # for d in new_id:
        #     if d in mpesa_lines:
        #         raise ValidationError(
        #             'Some of those mpesa records have been assigned. Please double check and remove records that have assiged checked!.')

        for rec in self.mpesa_messages:
            if rec.assigned == True:
                raise ValidationError(
                    'Remove all records whose assigned value is checked!')
        # mpesa_set = set()
        # mpesa_set.update(mpesa_lines)
        # # print('[mpesa_lines]', mpesa_set)

        # if mpesa_records is None:
        #     pass
        # else:
        #     record.mpesa_line = [(5, 0, 0)]

        #     for rec in mpesa_records:
        #         # if str(rec.message_id) in mpesa_set:
        #         vals = {
        #             'code': rec.sender_from,
        #             'message': rec.message,
        #             'amount': rec.amount,
        #             'message_id': rec.message_id
        #         }

        #         record.mpesa_line = [(0, 0, vals)]
        #         # else:
        #         #     print('dffffffffffffffffffffffffffffffffffffff')

        # record.mpesa_line = [(5, 0, 0)]
        for rec in self.mpesa_messages:
            vals = {
                'code': rec.code,
                'message': rec.message,
                'amount': rec.amount,
                'message_id': rec.message_id
            }

            message = self.env['station.mpesa.records'].search(
                [('message_id', '=', rec.message_id)])
            message.update({
                'assigned': True
            })

            record.mpesa_line = [(0, 0, vals)]
