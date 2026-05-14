# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class DrawingRegister(models.Model):
    """
    Drawing and document register for a construction project.
    Tracks: drawings, specifications, RFIs, shop drawings,
    as-built drawings, and all project documents with revision control.
    """
    _name = 'salaam.drawing.register'
    _description = 'Drawing & Document Register'
    _order = 'drawing_number'
    _inherit = ['mail.thread']

    project_id = fields.Many2one(
        'salaam.construction.project', string='Project',
        required=True, ondelete='cascade', index=True,
    )
    drawing_number = fields.Char(
        string='Drawing / Doc Number', required=True,
        help='e.g. SCY-STR-001-REV03',
    )
    name = fields.Char(string='Title / Description', required=True)

    document_type = fields.Selection([
        ('architectural',   'Architectural Drawing'),
        ('structural',      'Structural Drawing'),
        ('mep',             'MEP Drawing'),
        ('civil',           'Civil Drawing'),
        ('landscape',       'Landscape Drawing'),
        ('specification',   'Specification Document'),
        ('shop_drawing',    'Shop Drawing'),
        ('as_built',        'As-Built Drawing'),
        ('rfi',             'RFI (Request for Information)'),
        ('method_statement','Method Statement'),
        ('inspection',      'Inspection / Test Report'),
        ('permit',          'Permit / Approval'),
        ('other',           'Other'),
    ], string='Document Type', required=True)

    phase_id = fields.Many2one(
        'salaam.construction.phase', string='Related Phase',
        domain="[('project_id','=',project_id)]",
    )
    discipline = fields.Selection([
        ('architecture', 'Architecture'),
        ('structure',    'Structure'),
        ('mep',          'MEP'),
        ('civil',        'Civil'),
        ('landscape',    'Landscape'),
        ('geotechnical', 'Geotechnical'),
        ('fire',         'Fire Protection'),
        ('it',           'IT / ELV'),
    ], string='Discipline')

    # ── REVISION CONTROL ──────────────────────────────────────────────────────
    revision = fields.Char(
        string='Revision', default='A',
        help='Current revision e.g. A, B, C, 0, 1, 2, Rev03',
    )
    status = fields.Selection([
        ('issued_for_review',      'Issued for Review'),
        ('issued_for_approval',    'Issued for Approval'),
        ('approved',               'Approved for Construction'),
        ('approved_with_comments', 'Approved with Comments'),
        ('rejected',               'Rejected — Revise and Resubmit'),
        ('superseded',             'Superseded'),
        ('as_built',               'As-Built / Final'),
    ], string='Status', default='issued_for_review', tracking=True)

    issued_by = fields.Many2one('res.partner', string='Issued By')
    issued_date = fields.Date(string='Issue Date', default=fields.Date.today)
    received_date = fields.Date(string='Received Date')
    response_required_by = fields.Date(string='Response Required By')
    responded_date = fields.Date(string='Responded / Approved Date')

    # ── DISTRIBUTION ──────────────────────────────────────────────────────────
    distributed_to = fields.Many2many(
        'res.partner', string='Distributed To',
    )

    # ── CONTENT ───────────────────────────────────────────────────────────────
    description = fields.Text(string='Description / Comments')
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'drawing_attachment_rel', 'drawing_id', 'attachment_id',
        string='Files',
    )
    file_count = fields.Integer(
        string='Files', compute='_compute_file_count',
    )

    # ── RFI SPECIFIC ──────────────────────────────────────────────────────────
    rfi_response = fields.Text(
        string='RFI Response',
    )
    rfi_impact_cost = fields.Monetary(
        string='RFI Cost Impact',
        currency_field='currency_id',
    )
    rfi_impact_time = fields.Integer(
        string='RFI Time Impact (days)'
    )
    currency_id = fields.Many2one(
        related='project_id.currency_id', store=True,
    )

    @api.depends('attachment_ids')
    def _compute_file_count(self):
        for rec in self:
            rec.file_count = len(rec.attachment_ids)

    def action_get_attachment_view(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Attachments',
            'res_model': 'ir.attachment',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }
