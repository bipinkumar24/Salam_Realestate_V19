# -*- coding: utf-8 -*-
"""Extensions to existing Buruuj models for portal access.

Each external-facing model inherits portal.mixin which provides:
- `_compute_access_url` for portal-friendly URL generation
- `access_url` field
- `access_token` for unauthenticated access (we don't use this here, but
  it's available)

Additional methods added here:
- `_portal_get_for_partner` — class-level helper to filter records visible
  to a given portal partner
"""
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError


# ============================================================================
# PROJECT — visible to client (via partner_id)
# ============================================================================
class ProjectProject(models.Model):
    _name = "project.project"
    _inherit = ["project.project", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/projects/{rec.id}"

    def _get_portal_return_action(self):
        self.ensure_one()
        return self.env.ref("buruuj_project.action_project_project_buruuj")

    @api.model
    def _portal_get_for_partner(self, partner):
        """Return projects visible to this portal partner."""
        if not partner:
            return self.browse()
        # Client sees projects where they are the customer
        return self.search([("partner_id", "=", partner.id)])


# ============================================================================
# IPC — clients see their own client IPCs; subs see their own sub IPCs
# ============================================================================
class BuruujIPC(models.Model):
    _name = "buruuj.ipc"
    _inherit = ["buruuj.ipc", "portal.mixin"]

    portal_approved_by_partner = fields.Boolean(
        string="Approved by Counterparty",
        readonly=True, copy=False,
        help="Set when the client / subcontractor has approved this IPC via the portal.")
    portal_approved_at = fields.Datetime(readonly=True, copy=False)
    portal_approved_user_id = fields.Many2one(
        "res.users", readonly=True, copy=False,
        help="Portal user who approved the IPC.")

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/ipcs/{rec.id}"

    @api.model
    def _portal_get_for_partner(self, partner):
        if not partner:
            return self.browse()
        # Client sees IPCs on projects they own (type=client)
        # Sub sees IPCs where they are the subcontractor (type=subcontractor)
        return self.search([
            "|",
            "&", ("type", "=", "client"),
                  ("project_id.partner_id", "=", partner.id),
            "&", ("type", "=", "subcontractor"),
                  ("partner_id", "=", partner.id),
        ])

    def portal_action_approve(self):
        """Called by client portal to approve a Client IPC."""
        for rec in self:
            if rec.type != "client":
                raise UserError(_(
                    "Only Client IPCs can be approved via the client portal."))
            if rec.state != "finance_approved":
                raise UserError(_(
                    "IPC must be Finance Approved before client can approve it."))
            rec.write({
                "portal_approved_by_partner": True,
                "portal_approved_at": fields.Datetime.now(),
                "portal_approved_user_id": self.env.user.id,
            })
            rec.message_post(body=_(
                "Client portal approval recorded by %(user)s.",
                user=self.env.user.name))


# ============================================================================
# SUBCONTRACT — sub sees their own
# ============================================================================
class BuruujSubcontract(models.Model):
    _name = "buruuj.subcontract"
    _inherit = ["buruuj.subcontract", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/subcontracts/{rec.id}"

    @api.model
    def _portal_get_for_partner(self, partner):
        if not partner:
            return self.browse()
        return self.search([("partner_id", "=", partner.id)])


# ============================================================================
# WORK ORDER — sub sees their own
# ============================================================================
class BuruujWorkOrder(models.Model):
    _name = "buruuj.workorder"
    _inherit = ["buruuj.workorder", "portal.mixin"]

    portal_acknowledged = fields.Boolean(string="Acknowledged by Subcontractor",
                                            readonly=True, copy=False)
    portal_acknowledged_at = fields.Datetime(readonly=True, copy=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/workorders/{rec.id}"

    @api.model
    def _portal_get_for_partner(self, partner):
        if not partner:
            return self.browse()
        return self.search([
            ("subcontract_id.partner_id", "=", partner.id),
        ])

    def portal_acknowledge(self):
        for rec in self:
            rec.write({
                "portal_acknowledged": True,
                "portal_acknowledged_at": fields.Datetime.now(),
            })
            rec.message_post(body=_(
                "Acknowledged by subcontractor portal user %(user)s.",
                user=self.env.user.name))


# ============================================================================
# RFI — visible to consultant / client recipient
# ============================================================================
class BuruujRFI(models.Model):
    _name = "buruuj.rfi"
    _inherit = ["buruuj.rfi", "portal.mixin"]

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/rfis/{rec.id}"

    @api.model
    def _portal_get_for_partner(self, partner):
        if not partner:
            return self.browse()
        return self.search([("sent_to", "=", partner.id)])

    def portal_respond(self, response_text):
        """Portal user submits a response to the RFI."""
        for rec in self:
            if rec.state == "closed":
                raise UserError(_("This RFI is already closed."))
            rec.write({
                "response": response_text,
                "response_date": fields.Date.context_today(rec),
                "state": "responded",
            })
            rec.message_post(body=_(
                "Response submitted via portal by %(user)s.",
                user=self.env.user.name))


# ============================================================================
# VARIATION ORDER — client approves
# ============================================================================
class BuruujVariation(models.Model):
    _name = "buruuj.variation"
    _inherit = ["buruuj.variation", "portal.mixin"]

    portal_decision = fields.Selection([
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ], default="pending", readonly=True, copy=False)
    portal_decision_at = fields.Datetime(readonly=True, copy=False)
    portal_decision_notes = fields.Text(readonly=True, copy=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/variations/{rec.id}"

    @api.model
    def _portal_get_for_partner(self, partner):
        if not partner:
            return self.browse()
        return self.search([("project_id.partner_id", "=", partner.id)])

    def portal_decide(self, decision, notes=""):
        """Client portal decision: approved or rejected."""
        if decision not in ("approved", "rejected"):
            raise UserError(_("Invalid decision."))
        for rec in self:
            if rec.state not in ("submitted",):
                raise UserError(_(
                    "VO must be in Submitted state for client decision."))
            rec.write({
                "portal_decision": decision,
                "portal_decision_at": fields.Datetime.now(),
                "portal_decision_notes": notes,
            })
            if decision == "approved":
                rec.write({
                    "state": "approved",
                    "approval_date": fields.Date.context_today(rec),
                })
            else:
                rec.write({"state": "rejected"})
            rec.message_post(body=_(
                "Client portal decision: %(d)s by %(u)s. %(notes)s",
                d=decision, u=self.env.user.name,
                notes=f"Notes: {notes}" if notes else ""))


# ============================================================================
# DRAWING — client/consultant approval
# ============================================================================
class BuruujDrawing(models.Model):
    _name = "buruuj.drawing"
    _inherit = ["buruuj.drawing", "portal.mixin"]

    portal_response = fields.Selection([
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("approved_comments", "Approved with Comments"),
        ("rejected", "Rejected"),
    ], default="pending", readonly=True, copy=False)
    portal_response_at = fields.Datetime(readonly=True, copy=False)
    portal_response_notes = fields.Text(readonly=True, copy=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/drawings/{rec.id}"

    @api.model
    def _portal_get_for_partner(self, partner):
        if not partner:
            return self.browse()
        return self.search([
            ("project_id.partner_id", "=", partner.id),
            ("purpose", "=", "approval"),
        ])

    def portal_review(self, response, notes=""):
        if response not in ("approved", "approved_comments", "rejected"):
            raise UserError(_("Invalid response."))
        for rec in self:
            rec.write({
                "portal_response": response,
                "portal_response_at": fields.Datetime.now(),
                "portal_response_notes": notes,
            })
            # Map portal response to drawing status
            status_map = {
                "approved": "approved",
                "approved_comments": "approved_with_comments",
                "rejected": "rejected",
            }
            rec.write({"status": status_map[response]})
            rec.message_post(body=_(
                "Drawing reviewed via portal: %(r)s. %(notes)s",
                r=response, notes=f"Notes: {notes}" if notes else ""))


# ============================================================================
# BACKCHARGE — sub sees their own with dispute flag
# ============================================================================
class BuruujBackcharge(models.Model):
    _name = "buruuj.backcharge"
    _inherit = ["buruuj.backcharge", "portal.mixin"]

    portal_disputed = fields.Boolean(string="Disputed by Subcontractor",
                                       readonly=True, copy=False)
    portal_dispute_reason = fields.Text(readonly=True, copy=False)
    portal_dispute_at = fields.Datetime(readonly=True, copy=False)

    def _compute_access_url(self):
        super()._compute_access_url()
        for rec in self:
            rec.access_url = f"/my/backcharges/{rec.id}"

    @api.model
    def _portal_get_for_partner(self, partner):
        if not partner:
            return self.browse()
        return self.search([
            ("subcontract_id.partner_id", "=", partner.id),
        ])

    def portal_dispute(self, reason):
        if not reason:
            raise UserError(_(
                "Please provide a reason for the dispute."))
        for rec in self:
            rec.write({
                "portal_disputed": True,
                "portal_dispute_reason": reason,
                "portal_dispute_at": fields.Datetime.now(),
            })
            rec.message_post(body=_(
                "Disputed via portal by %(u)s: %(r)s",
                u=self.env.user.name, r=reason))


# ============================================================================
# RES PARTNER — count helpers for portal landing page
# ============================================================================
class ResPartner(models.Model):
    _inherit = "res.partner"

    def _portal_get_counts(self):
        """Return dict of counts for the portal home page."""
        self.ensure_one()
        env = self.env
        # Client side
        projects = env["project.project"]._portal_get_for_partner(self)
        client_ipcs = env["buruuj.ipc"]._portal_get_for_partner(self).filtered(
            lambda i: i.type == "client")
        ipcs_pending = client_ipcs.filtered(
            lambda i: i.state == "finance_approved"
                      and not i.portal_approved_by_partner)
        rfis = env["buruuj.rfi"]._portal_get_for_partner(self)
        rfis_open = rfis.filtered(lambda r: r.state in ("sent",))
        variations = env["buruuj.variation"]._portal_get_for_partner(self)
        variations_pending = variations.filtered(
            lambda v: v.state == "submitted"
                      and v.portal_decision == "pending")
        drawings = env["buruuj.drawing"]._portal_get_for_partner(self)
        drawings_pending = drawings.filtered(
            lambda d: d.portal_response == "pending"
                      and d.purpose == "approval")

        # Sub side
        subs = env["buruuj.subcontract"]._portal_get_for_partner(self)
        wos = env["buruuj.workorder"]._portal_get_for_partner(self)
        wos_unack = wos.filtered(lambda w: not w.portal_acknowledged
                                            and w.state in ("issued", "in_progress"))
        sub_ipcs = env["buruuj.ipc"]._portal_get_for_partner(self).filtered(
            lambda i: i.type == "subcontractor")
        backcharges = env["buruuj.backcharge"]._portal_get_for_partner(self)
        backcharges_open = backcharges.filtered(
            lambda b: b.state == "confirmed" and not b.portal_disputed)

        return {
            "projects": len(projects),
            "client_ipcs": len(client_ipcs),
            "ipcs_pending": len(ipcs_pending),
            "rfis": len(rfis_open),
            "variations_pending": len(variations_pending),
            "drawings_pending": len(drawings_pending),
            "subs": len(subs),
            "wos_unack": len(wos_unack),
            "sub_ipcs": len(sub_ipcs),
            "backcharges_open": len(backcharges_open),
            "is_client": self.customer_rank > 0,
            "is_sub": getattr(self, "is_subcontractor", False),
        }
