from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import requests
import json

def getting_ip(row):
    """This function calls the api and return the response"""
    url = f"https://ipapi.co/{row}/json/"       # getting records from getting ip address
    headers = {
        'accept': "application/json",
        'content-type': "application/json",
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36'
        }
    response = requests.request("GET", url, headers=headers)
    respond = json.loads(response.text)
    return respond

class Controller(http.Controller):

    @http.route('/post/action_data', type='jsonrpc', auth='public')
    def _get_action_data(self, data={}, **kw):
        ip_response = self._get_ip_params()
        api = ''
        if not ip_response.get('api_response').get('error'):
            api = ip_response.get('api_response').get('ip') 
        
        try:
            # original_url = data
            activity_log_obj = request.env['activity.log'].sudo()
            menu_obj = request.env['ir.ui.menu'].sudo()
            config_parameter_obj = request.env['ir.config_parameter'].sudo()
            # login_log = request.env['login.log'].sudo().search([('session_id','=',request.session.sid)],limit=1)
            login_log = request.env['res.device.log'].sudo().search([('session_identifier','=',request.session.sid[:42])],limit=1)
            if not login_log.ip_address and api:
                login_log.ip = api
                try:
                    
                    value = getting_ip(api)
                    country = value['country_name'] or ''
                    city = value['city'] or ''
                    # state = value['region'] or ''
                except:
                    country = ''
                    # state = ''
                    city = ''
                login_log.sudo().write({
                    'ip_address':api,
                    'country':country,
                    'city':city
                })
            url = config_parameter_obj.get_param('web.base.url')
            active_timeout = config_parameter_obj.get_param('advanced_session_management.session_timeout_active') or 'none'
            if active_timeout in ['active', 'inactive']:
                interval_number = int(config_parameter_obj.get_param('advanced_session_management.remove_sesions'))
                if interval_number > 0:
                    # login_log.timeout_date = datetime.now() + timedelta(hours=interval_number)
                    login_log.timeout_date = datetime.now() + timedelta(days=interval_number)
            
            # full_url = url + '/web#'
            # for record in data:
            #     full_url +=  record + '=' + str(data[record]) + '&'
            
            # full_url = full_url[:len(full_url)-1]
            # full_url = url + '/odoo/'
            # for record in data:
            #     full_url +=  record 
            if 'action' in data.keys() and data['action'] == 'menu':
                activity_log_obj.create({
                    'name':"Open Home Screen",
                    'action':'read',
                    # 'login_log_id':login_log.id,
                    'device_id':login_log.id,
                    'user_id':login_log.user_id.id,
                    'url': '/odoo',
                    'model':'n/a',
                    'view':'n/a',
                })
            else:
                name = ''
                res_model = ''
                res_id = 0
                view_type = ''
                full_url = ''
                # ir.actions.act_window
                if 'actionStack' in data.keys():
                    for action in data['actionStack']:
                        view_type = action.get('view_type')
                        full_url = '/odoo/' + action.get('action')
                        res_model = request.env['ir.actions.act_window'].search([('path','=',action.get('action'))],limit=1).res_model
                        if 'resId' in action:
                            full_url += '/' + str(action.get('resId'))
                            record = request.env[res_model].search([('id','=',action.get('resId'))],limit=1)
                            res_id = action.get('resId')
                            if record:
                                try:
                                    if record.name: 
                                        name = record.name
                                    else:
                                        name = record.display_name
                                except:
                                    name = record.display_name
                        else:
                            name = action.get('displayName')
                            
                # if data.get('id'):
                #     record = request.env[data.get('model')].search([('id','=',data.get('id'))],limit=1)
                #     if record:
                #         try:
                #             if record.name:
                #                 name = record.name
                #             else:
                #                 name = record.display_name
                #         except:
                #             name = record.display_name
                # if not name:
                #     name = data.get('name')
                    # menu = menu_obj.search([('id','=',data.get('menu_id'))],limit=1)
                    # if menu:
                    #     name = menu.name
                    
                if name:
                    activity_log_obj.create({
                        'name':name,
                        'model':res_model or 'n/a',
                        'res_id':res_id or 'n/a',
                        'action':'read',
                        'view':view_type or 'n/a',
                        # 'login_log_id':login_log.id,
                        'device_id':login_log.id,
                        'user_id':login_log.user_id.id,
                        'url':full_url,
                        # 'view':'n/a',
                    })
                    pass
        except:
            pass
        
        return 

     
    def _get_ip_params(self):
        vals = {}
        config_parameter_obj = request.env['ir.config_parameter'].sudo()
        ip_url = config_parameter_obj.get_param('advanced_session_management.ip_url') or 'none'
        ip_key = config_parameter_obj.get_param('advanced_session_management.ip_key') or 'none'
    
        vals['ip_url'] = ip_url
        vals['ip_key'] = ip_key
        if ip_url != 'none':
            try:
                # Making the API request
                headers = {'Authorization': f'Bearer {ip_key}'} if ip_key != 'none' else {}
                response = requests.get(ip_url, headers=headers, timeout=10)
                
                # Handling the response
                if response.status_code == 200:
                    vals['api_response'] = response.json()  # Parse JSON response
                else:
                    vals['api_response'] = {
                        'error': f"Failed to fetch data. Status code: {response.status_code}",
                        'details': response.text,
                    }
            except requests.exceptions.RequestException as e:
                vals['api_response'] = {
                    'error': 'Exception occurred while fetching data from API',
                    'details': str(e),
                }
        else:
            vals['api_response'] = {
                'error': 'IP URL not configured properly',
            }
        return vals 