# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujDrawing(models.Model):
    _name = 'buruuj.drawing'
    _description = 'Drawing Register'
    _inherit = ['mail.thread']
    _order = 'project_id, drawing_no'

    name = fields.Char(compute='_compute_name', store=True)
    drawing_no = fields.Char(string='Drawing No.', required=True, copy=False)
    title = fields.Char(required=True)
    project_id = fields.Many2one('project.project', required=True, tracking=True)
    discipline = fields.Selection([
        ('arch', 'Architectural'),
        ('struct', 'Structural'),
        ('mep', 'MEP'),
        ('civil', 'Civil'),
        ('landscape', 'Landscape'),
        ('other', 'Other'),
    ], default='arch', required=True)
    revision = fields.Char(default='R0', tracking=True)
    sheet_size = fields.Selection([
        ('a0', 'A0'), ('a1', 'A1'), ('a2', 'A2'),
        ('a3', 'A3'), ('a4', 'A4'),
    ])
    scale = fields.Char()
    drawn_by = fields.Char()
    checked_by = fields.Char()
    issue_date = fields.Date()
    purpose = fields.Selection([
        ('information', 'For Information'),
        ('approval', 'For Approval'),
        ('construction', 'For Construction'),
        ('asbuilt', 'As-Built'),
    ], default='approval')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('approved_with_comments', 'Approved with Comments'),
        ('rejected', 'Rejected'),
        ('superseded', 'Superseded'),
    ], default='draft', tracking=True)
    file_attachment = fields.Binary()
    file_name = fields.Char()
    notes = fields.Text()

    @api.depends('drawing_no', 'title', 'revision')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.drawing_no or ''} {rec.revision or ''} - {rec.title or ''}"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('drawing_no'):
                vals['drawing_no'] = self.env['ir.sequence'].next_by_code(
                    'buruuj.drawing') or 'DWG/NEW'
        return super().create(vals_list)
