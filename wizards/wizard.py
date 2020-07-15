from odoo import api, fields, models


class MpesaRecordsWizard(models.TransientModel):
    _name = 'mpesa.records.wizard'
    _description = 'Get Mpesa Records for a particular date'

    date = fields.Date(string='Date', default=fields.Datetime.now())

    def action_add_mpesa_records(self):
        '''
        Get all the mpesa records and populate them in the current station sale record
        '''
        record = self.env['station.sales'].browse(
            self._context.get('active_ids', []))

        mpesa_records = self.env['station.mpesa.records'].search(
            [("date", "=", self.date.strftime('%Y-%m-%d'))])
        mpesa_lines = self.env['mpesa.line'].search(
            []).mapped('message_id')
        mpesa_set = set()
        mpesa_set.update(mpesa_lines)
        # print('[mpesa_lines]', mpesa_set)

        if mpesa_records is None:
            pass
        else:
            record.mpesa_line = [(5, 0, 0)]

            for rec in mpesa_records:
                # if str(rec.message_id) in mpesa_set:
                vals = {
                    'code': rec.sender_from,
                    'message': rec.message,
                    'amount': rec.amount,
                    'message_id': rec.message_id
                }

                record.mpesa_line = [(0, 0, vals)]
                # else:
                #     print('dffffffffffffffffffffffffffffffffffffff')
