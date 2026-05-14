# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class DocumentAttachment(models.Model):
    _name = 'bre.document.attachment'
    _description = 'Application Document Attachment'
    _inherit = ['mail.thread']
    _order = 'create_date desc'

    name = fields.Char(string='Document Name', required=True)
    application_id = fields.Many2one('bre.customer.application', string='Application',
                                     required=True, ondelete='cascade')
    document_type_id = fields.Many2one('bre.document.type', string='Document Type', required=True)
    document_category = fields.Selection([
        ('identification', 'Identification'),
        ('financial', 'Financial'),
        ('property', 'Property'),
        ('employment', 'Employment'),
        ('sharia', 'Sharia Related'),
        ('other', 'Other'),
    ], string='Category', required=True, default='other')

    # File
    attachment_ids = fields.Many2many('ir.attachment', string='Files',
                                      relation='bre_doc_attachment_ir_attachment_rel')
    file_count = fields.Integer(string='Files', compute='_compute_file_count')

    # Status
    verification_status = fields.Selection([
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected / Invalid'),
        ('expired', 'Expired'),
    ], string='Verification Status', default='pending', tracking=True)

    verified_by = fields.Many2one('res.users', string='Verified By', readonly=True)
    verified_date = fields.Datetime(string='Verified Date', readonly=True)
    expiry_date = fields.Date(string='Document Expiry Date')
    rejection_reason = fields.Text(string='Rejection Reason')
    notes = fields.Text(string='Notes')

    # Submitted by
    submitted_by = fields.Many2one('res.users', string='Submitted By',
                                   default=lambda self: self.env.user)
    submission_date = fields.Date(string='Submission Date', default=fields.Date.today)

    is_mandatory = fields.Boolean(related='document_type_id.is_mandatory', string='Mandatory')

    @api.depends('attachment_ids')
    def _compute_file_count(self):
        for rec in self:
            rec.file_count = len(rec.attachment_ids)

    def action_verify(self):
        self.write({
            'verification_status': 'verified',
            'verified_by': self.env.user.id,
            'verified_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Document verified by %s.') % self.env.user.name,
                          subtype_xmlid='mail.mt_note')

    def action_reject_doc(self):
        self.write({'verification_status': 'rejected'})

    def action_mark_expired(self):
        self.write({'verification_status': 'expired'})

    @api.model
    def get_documents_summary(self, application_id):
        docs = self.search([('application_id', '=', application_id)])
        return {
            'total': len(docs),
            'verified': len(docs.filtered(lambda d: d.verification_status == 'verified')),
            'pending': len(docs.filtered(lambda d: d.verification_status == 'pending')),
            'rejected': len(docs.filtered(lambda d: d.verification_status == 'rejected')),
        }
