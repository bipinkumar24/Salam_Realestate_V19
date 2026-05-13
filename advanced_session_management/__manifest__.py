# -*- coding: utf-8 -*-
#################################################################################
# Author      : Terabits Technolab (<www.terabits.xyz>)
# Copyright(c): 2021-25
# All Rights Reserved.
#
# This module is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
{
    'name': 'Advanced User Audit | User Activity Audit | Login Notification',
    'version': '19.0.1.0.0',
    'summary': 'User Activity Log, User Activity Audit,  Session Management, Record Log, Activity Traces, Login Notification, User Activity Record, Record History, Login History, Login location, Login IP',
    'sequence': 6,
    'author': 'Terabits Technolab',
    'license': 'OPL-1',
    'category': 'Services',
    'website': 'https://www.terabits.xyz/apps/19.0/advanced_session_management',
    'description':"""
        Advanced User Audit makes it-
        Easy to track all the activities performed by the internal users in odoo. 
        East to trace which activity performed by which user on which login session,
        Easy to audit the user activities in odoo,
        Easy to track all the sessions started by internal users,
        Easy to track the operations like create, update and delete performed in individual sessions,
        User can see the information of any session like: IP, date, device, location, os & browser,
        User will get instant email notification if any new sessions starts to alarm the users
        Follow Users Traces, Audit Trail, User Log, Log Report, Record Log, Record Information, User Activity log, Record History, Log History, User Activity Audit Log,
        Manage Audit Logs, Track every Users Operation, Delete Log, audit user activity Odoo, Log all user login,Log audit, Login audit,Show User online status
    """, 
    "price": "199.99",
    "currency": "USD",
    'depends':['mail','auth_oauth','http_routing'],
    'data':[
        'security/ir.model.access.csv',
        'security/res_groups.xml',
        'data/cron.xml',
        'data/email_template.xml',
        'views/res_config_settings_view.xml',
        'views/login_log_view.xml',
        'views/res_device_views.xml',
        'views/activity_log_view.xml',
        'views/res_user_view.xml',
        # 'views/assets.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'advanced_session_management/static/src/scss/style.scss',
            'advanced_session_management/static/src/js/router_service.js',
        ],
    },
    'external_dependencies': {
        'python': ['user_agents']
    },
    'application': True,
    'installable': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'live_test_url': 'https://www.terabits.xyz/request_demo?source=index&version=16&app=advanced_session_management',
    'images': ['static/description/banner.gif'],
}
