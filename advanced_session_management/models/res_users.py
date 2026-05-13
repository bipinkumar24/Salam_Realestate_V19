from odoo import fields, models, api,  SUPERUSER_ID, _
from user_agents import parse
from odoo.http import request
from datetime import datetime,timedelta

class res_users(models.Model):
    _inherit = 'res.users'

    login_log_ids = fields.One2many('login.log', 'user_id', 'Sessions')

    def action_kill_all_session(self):
        for record in self:
            return record.login_log_ids.logout_button()

    # @classmethod
    def _login(self, credential, user_agent_env):
        res = super(res_users, self)._login(credential, user_agent_env)
        try:            
            with self.pool.cursor() as cr:   
                # self = api.Environment(cr, SUPERUSER_ID, {})
                login_log_obj = self.env['login.log'].sudo()
                partner_obj = self.env['res.partner'].sudo()
                
                if not self.env['res.users'].sudo().browse(res.get('uid')).has_group('base.group_portal'):
                    user_agent = parse(request.httprequest.environ.get('HTTP_USER_AGENT', ''))
                    device = user_agent.device.family
                    if user_agent.device.family == 'Other':
                        if user_agent.is_pc:
                            device = 'PC'
                        elif user_agent.is_mobile:
                            device = 'Mobile'
                        elif user_agent.is_tablet:
                            device = 'Tablet'
                        
                    if not login_log_obj.search([('user_agent','=',request.session.sid)], limit=1).id:
                        login_log = login_log_obj.create({
                            'login_date':datetime.now(),
                            'user_id':res.get('uid'),
                            'user_agent':request.session.sid,
                            'state':'active',
                            # 'ip':ip,
                            'browser':user_agent.browser.family,
                            # 'session_id':request.session.sid,
                            'device':device,
                            'os':user_agent.os.family,
                            # 'country':country,
                            # 'loc_state':state,
                            # 'city':city
                        })
                        config_parameter_obj = self.env['ir.config_parameter'].sudo()
                        active_timeout = config_parameter_obj.get_param('advanced_session_management.session_timeout_active') or 'none'
                        if active_timeout != 'none':
                            interval_number = int(config_parameter_obj.get_param('advanced_session_management.session_timeout_interval_number'))
                            if interval_number:
                                login_log.timeout_date = datetime.now() + timedelta(days=interval_number)
        except:
            pass
        return res
            
