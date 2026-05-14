# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BuruujToolboxTalk(models.Model):
    _name = 'buruuj.toolbox.talk'
    _description = 'Toolbox Talk'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    topic = fields.Char(required=True)
    conducted_by = fields.Many2one('res.users', default=lambda s: s.env.user)
    attendee_count = fields.Integer(string='Attendees')
    notes = fields.Html()
    attachment_ids = fields.Many2many('ir.attachment',
                                        string='Attendance Sheet / Photos')
    state = fields.Selection([
        ('draft', 'Draft'), ('done', 'Conducted'),
    ], default='draft')

    def action_done(self):
        self.state = 'done'
