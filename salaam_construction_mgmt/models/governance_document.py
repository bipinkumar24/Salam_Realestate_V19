# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class GovernanceDocument(models.Model):
    """
    Corporate Governance Document management.
    Covers: MOA, AOA, Board Resolutions, JV Agreements, Shareholder Agreements,
    Regulatory Approvals, Sharia Board Minutes, Power of Attorney, etc.
    Each document is versioned, tracked, and linked to the project it governs.
    """
    _name = 'salaam.governance.document'
    _description = 'Governance Document'
    _order = 'doc_type, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Document Title', required=True, tracking=True)
    reference = fields.Char(
        string='Document Reference', copy=False,
        default=lambda self: _('New'),
    )

    # ── CLASSIFICATION ────────────────────────────────────────────────────────
    doc_type = fields.Many2one(
        'salaam.governance.doc.type',
        string='Document Type', required=True,
    )
    doc_category = fields.Selection([
        ('constitutional',  'Constitutional Document'),
        ('board',           'Board & Shareholder'),
        ('regulatory',      'Regulatory & Permits'),
        ('sharia',          'Sharia Governance'),
        ('financial',       'Financial & Audit'),
        ('legal',           'Legal & Contracts'),
        ('jv',              'Joint Venture'),
        ('hr',              'HR & Staffing'),
        ('other',           'Other'),
    ], string='Category', required=True, tracking=True)

    state = fields.Selection([
        ('draft',       'Draft'),
        ('in_review',   'Under Review'),
        ('approved',    'Approved / Executed'),
        ('superseded',  'Superseded'),
        ('expired',     'Expired'),
        ('archived',    'Archived'),
    ], string='Status', default='draft', tracking=True)

    # ── PROJECT & CONTRACT LINKS ──────────────────────────────────────────────
    project_id = fields.Many2one(
        'salaam.construction.project', string='Related Project',
        ondelete='set null', index=True,
    )
    musharaka_id = fields.Many2one(
        'dev.contract.musharaka', string='Related Musharaka Contract',
        ondelete='set null',
        help='For JV/Partnership constitutional documents',
    )
    company_id = fields.Many2one(
        'res.company', string='Branch / Entity',
        default=lambda self: self.env.company,
    )

    # ── PARTIES & SIGNATORIES ─────────────────────────────────────────────────
    issuing_authority = fields.Char(
        string='Issuing Authority / Jurisdiction',
        help='e.g. Republic of Djibouti Ministry of Commerce',
    )
    party_ids = fields.Many2many(
        'res.partner', string='Parties / Signatories',
    )
    signed_by_bank = fields.Boolean(string='Signed by Bank')
    bank_signatory_id = fields.Many2one(
        'res.users', string='Bank Authorised Signatory',
    )

    # ── DATES & VALIDITY ──────────────────────────────────────────────────────
    execution_date = fields.Date(string='Execution / Issue Date')
    effective_date = fields.Date(string='Effective Date')
    expiry_date = fields.Date(string='Expiry / Renewal Date')
    renewal_required = fields.Boolean(string='Renewal Required')
    days_to_expiry = fields.Integer(
        string='Days to Expiry', compute='_compute_days_to_expiry', store=True,
    )

    # ── VERSION CONTROL ───────────────────────────────────────────────────────
    version = fields.Char(string='Version', default='1.0')
    supersedes_id = fields.Many2one(
        'salaam.governance.document',
        string='Supersedes (Previous Version)',
    )

    # ── CONTENT ───────────────────────────────────────────────────────────────
    summary = fields.Html(string='Executive Summary')
    key_provisions = fields.Html(string='Key Provisions')
    confidentiality_level = fields.Selection([
        ('public',          'Public'),
        ('internal',        'Internal'),
        ('restricted',      'Restricted'),
        ('strictly_confidential', 'Strictly Confidential'),
    ], string='Confidentiality Level', default='restricted')

    attachment_ids = fields.Many2many(
        'ir.attachment',
        'governance_doc_attachment_rel', 'doc_id', 'attachment_id',
        string='Document Files',
    )
    file_count = fields.Integer(
        string='Files', compute='_compute_file_count',
    )
    notes = fields.Text(string='Internal Notes')

    # ── COMPUTED ──────────────────────────────────────────────────────────────
    @api.depends('expiry_date')
    def _compute_days_to_expiry(self):
        from datetime import date
        today = date.today()
        for rec in self:
            if rec.expiry_date:
                rec.days_to_expiry = (rec.expiry_date - today).days
            else:
                rec.days_to_expiry = 0

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', _('New')) == _('New'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'salaam.governance.document'
                ) or _('New')
        return super().create(vals_list)

    # ── WORKFLOW ──────────────────────────────────────────────────────────────
    def action_submit_review(self):
        self.write({'state': 'in_review'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_supersede(self):
        self.write({'state': 'superseded'})

    def action_archive_doc(self):
        self.write({'state': 'archived'})


class GovernanceDocType(models.Model):
    """Configurable document type taxonomy for governance documents."""
    _name = 'salaam.governance.doc.type'
    _description = 'Governance Document Type'
    _order = 'name'

    name = fields.Char(string='Document Type', required=True)
    code = fields.Char(string='Code')
    category = fields.Selection([
        ('constitutional',  'Constitutional'),
        ('board',           'Board & Shareholder'),
        ('regulatory',      'Regulatory'),
        ('sharia',          'Sharia Governance'),
        ('financial',       'Financial'),
        ('legal',           'Legal'),
        ('jv',              'Joint Venture'),
        ('other',           'Other'),
    ], string='Category')
    description = fields.Text(string='Description')
    active = fields.Boolean(default=True)
