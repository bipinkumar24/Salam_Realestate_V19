from odoo import api, fields, models, _
from datetime import datetime, timedelta

class ResDeviceLog(models.Model):
    _inherit = 'res.device.log'

    activity_log_ids = fields.One2many('activity.log', 'device_id', 'Activity Logs')
    timeout_date = fields.Datetime('Last Activity')

    def session_timeout_ah(self):
        config_parameter_obj = self.env['ir.config_parameter'].sudo()
        active_timeout = config_parameter_obj.get_param('advanced_session_management.session_timeout_active')

        if active_timeout == 'active':
            self.search([('is_current','=', True),('timeout_date','<',datetime.now())])._revoke()

        elif active_timeout == 'inactive':
            self.search([('timeout_date','<',datetime.now())])._revoke()

    def remove_old_log(self):
        config_parameter_obj = self.env['ir.config_parameter']
        value = config_parameter_obj.search([('key','=','advanced_session_management.remove_sesions')],limit=1)
        if value and value.value:
            value = int(value.value)
        else:
            value = 7
        self.search([('is_current','=',False),('last_activity','<=',datetime.now() - timedelta(value))]).unlink()
        self.env['activity.log'].search([('create_date','<=',datetime.now() - timedelta(value))]).unlink()


    def _update_device(self, request):
        pass
        res = super(ResDeviceLog, self)._update_device(request)
        trace = request.session.update_trace(request)
        if trace:
            pass

    def dummy_btn(self):
        pass