# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class PropertyHandoverInherit(models.Model):
    _inherit = 'property.details'

    snag_list_ids = fields.One2many(
        'salaam.snag.list', 'property_id', string='Snag Lists',
    )
    handover_certificate_ids = fields.One2many(
        'salaam.handover.certificate', 'property_id', string='Handover Certificates',
    )
    warranty_claim_ids = fields.One2many(
        'salaam.warranty.claim', 'property_id', string='Warranty Claims',
    )
    snag_count = fields.Integer(compute='_compute_handover_counts')
    certificate_count = fields.Integer(compute='_compute_handover_counts')
    warranty_count = fields.Integer(compute='_compute_handover_counts')
    open_warranty_count = fields.Integer(compute='_compute_handover_counts')
    handover_date = fields.Date(
        compute='_compute_handover_counts', store=True,
        string='Handover Date',
    )
    dlp_end_date = fields.Date(
        compute='_compute_handover_counts', store=True,
        string='DLP End Date',
    )

    @api.depends(
        'snag_list_ids', 'handover_certificate_ids',
        'warranty_claim_ids', 'warranty_claim_ids.state',
        'handover_certificate_ids.handover_date',
        'handover_certificate_ids.dlp_end_date',
        'handover_certificate_ids.state',
    )
    def _compute_handover_counts(self):
        for rec in self:
            rec.snag_count = len(rec.snag_list_ids)
            rec.certificate_count = len(rec.handover_certificate_ids)
            rec.warranty_count = len(rec.warranty_claim_ids)
            rec.open_warranty_count = len(
                rec.warranty_claim_ids.filtered(
                    lambda w: w.state not in ('closed', 'rejected', 'maintenance_only')
                )
            )
            # Pull handover date from latest signed certificate
            signed = rec.handover_certificate_ids.filtered(
                lambda c: c.state in ('buyer_signed', 'registered')
            ).sorted('handover_date', reverse=True)
            if signed:
                rec.handover_date = signed[0].handover_date
                rec.dlp_end_date = signed[0].dlp_end_date
            else:
                rec.handover_date = False
                rec.dlp_end_date = False
