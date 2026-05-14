# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujMR(models.Model):
    """Material Requisition raised by site, actioned by procurement."""
    _name = "buruuj.material.requisition"
    _description = "Material Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"
    _rec_name = "name"

    name = fields.Char(copy=False, default=lambda s: _("New"), tracking=True)
    project_id = fields.Many2one("project.project", required=True,
                                   tracking=True)
    phase_id = fields.Many2one("buruuj.phase", string="Project Phase",
                                 domain="[('project_id','=',project_id)]")
    requested_by = fields.Many2one("res.users",
                                     default=lambda s: s.env.user,
                                     tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    required_by = fields.Date(string="Required On Site By", required=True,
                                tracking=True)
    priority = fields.Selection([
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ], default="normal", tracking=True)

    line_ids = fields.One2many("buruuj.material.requisition.line",
                                 "mr_id", string="Materials")
    line_count = fields.Integer(compute="_compute_line_count")

    rfq_ids = fields.One2many("buruuj.rfq", "mr_id")
    rfq_count = fields.Integer(compute="_compute_rfq_count")

    purpose = fields.Text(string="Purpose / Justification")
    rejection_reason = fields.Text()

    state = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted to Procurement"),
        ("approved", "PM Approved"),
        ("in_rfq", "RFQ Issued"),
        ("po_raised", "PO Raised"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    @api.depends("line_ids")
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends("rfq_ids")
    def _compute_rfq_count(self):
        for rec in self:
            rec.rfq_count = len(rec.rfq_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.material.requisition") or _("New")
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_(
                    "Add at least one material line before submitting."))
            rec.state = "submitted"

    def action_pm_approve(self):
        for rec in self:
            if rec.state != "submitted":
                raise UserError(_("Only submitted MRs can be approved."))
            rec.state = "approved"

    def action_reject(self):
        for rec in self:
            if not rec.rejection_reason:
                raise UserError(_(
                    "Please enter a rejection reason."))
            rec.state = "rejected"

    def action_cancel(self):
        self.state = "cancelled"

    def action_close(self):
        self.state = "closed"

    def action_create_rfq(self):
        """Create an RFQ from this MR."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(_(
                "MR must be PM-approved before raising an RFQ."))
        rfq = self.env["buruuj.rfq"].create({
            "mr_id": self.id,
            "project_id": self.project_id.id,
        })
        # Copy MR lines to RFQ lines
        for ml in self.line_ids:
            self.env["buruuj.rfq.line"].create({
                "rfq_id": rfq.id,
                "material_id": ml.material_id.id,
                "specification": ml.specification,
                "quantity": ml.quantity,
                "uom_id": ml.uom_id.id,
            })
        self.state = "in_rfq"
        return {
            "type": "ir.actions.act_window",
            "res_model": "buruuj.rfq",
            "res_id": rfq.id,
            "view_mode": "form",
        }

    def action_view_rfqs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("RFQs"),
            "res_model": "buruuj.rfq",
            "view_mode": "list,form",
            "domain": [("mr_id", "=", self.id)],
            "context": {"default_mr_id": self.id,
                          "default_project_id": self.project_id.id},
        }


class BuruujMRLine(models.Model):
    _name = "buruuj.material.requisition.line"
    _description = "Material Requisition Line"
    _order = "sequence, id"

    mr_id = fields.Many2one("buruuj.material.requisition",
                              required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    material_id = fields.Many2one("buruuj.material", required=True)
    specification = fields.Char(
        help="Item-specific spec override; defaults to material master.")
    quantity = fields.Float(required=True, default=1.0)
    uom_id = fields.Many2one("uom.uom", required=True)
    estimated_unit_price = fields.Monetary()
    estimated_total = fields.Monetary(compute="_compute_estimated_total",
                                        store=True)
    notes = fields.Char()
    currency_id = fields.Many2one(
        "res.currency", related="mr_id.company_id.currency_id")

    @api.onchange("material_id")
    def _onchange_material(self):
        if self.material_id:
            self.uom_id = self.material_id.uom_id
            if not self.specification:
                self.specification = self.material_id.specification
            if self.material_id.last_purchase_price and not self.estimated_unit_price:
                self.estimated_unit_price = self.material_id.last_purchase_price

    @api.depends("quantity", "estimated_unit_price")
    def _compute_estimated_total(self):
        for rec in self:
            rec.estimated_total = rec.quantity * rec.estimated_unit_price
