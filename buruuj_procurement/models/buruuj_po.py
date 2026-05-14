# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujPO(models.Model):
    """Purchase Order with QS → PM → Director approval workflow."""
    _name = "buruuj.po"
    _description = "Purchase Order"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(copy=False, default=lambda s: _("New"), tracking=True)
    rfq_id = fields.Many2one("buruuj.rfq", string="Source RFQ", tracking=True)
    mr_id = fields.Many2one("buruuj.material.requisition",
                              string="Source MR")
    project_id = fields.Many2one("project.project", required=True,
                                   tracking=True)
    vendor_id = fields.Many2one(
        "res.partner", string="Vendor", required=True, tracking=True,
        domain=[("supplier_rank", ">", 0)])

    date = fields.Date(default=fields.Date.context_today, required=True,
                         tracking=True)
    expected_delivery = fields.Date(string="Expected Delivery", tracking=True)

    delivery_address = fields.Text()
    delivery_terms = fields.Char()
    payment_terms = fields.Char()
    incoterm = fields.Char()
    vat_rate = fields.Float(string="VAT %", default=15.0)

    line_ids = fields.One2many("buruuj.po.line", "po_id")
    grn_ids = fields.One2many("buruuj.grn", "po_id")
    grn_count = fields.Integer(compute="_compute_grn_count")

    subtotal = fields.Monetary(compute="_compute_totals", store=True)
    vat_amount = fields.Monetary(compute="_compute_totals", store=True)
    total_amount = fields.Monetary(compute="_compute_totals", store=True)

    qs_approved_by = fields.Many2one("res.users", readonly=True,
                                       tracking=True)
    qs_approved_date = fields.Datetime(readonly=True)
    pm_approved_by = fields.Many2one("res.users", readonly=True,
                                       tracking=True)
    pm_approved_date = fields.Datetime(readonly=True)
    director_approved_by = fields.Many2one("res.users", readonly=True,
                                             tracking=True)
    director_approved_date = fields.Datetime(readonly=True)
    director_required = fields.Boolean(
        compute="_compute_director_required", store=True,
        help="True if PO value exceeds the threshold requiring Director approval.")

    notes = fields.Html()

    state = fields.Selection([
        ("draft", "Draft"),
        ("qs_approved", "QS Approved"),
        ("pm_approved", "PM Approved"),
        ("approved", "Fully Approved"),
        ("issued", "Issued to Vendor"),
        ("partial", "Partially Received"),
        ("received", "Fully Received"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)

    # Threshold above which Director approval is required
    DIRECTOR_THRESHOLD = 50000.0

    @api.depends("line_ids.line_total", "vat_rate")
    def _compute_totals(self):
        for rec in self:
            rec.subtotal = sum(rec.line_ids.mapped("line_total"))
            rec.vat_amount = rec.subtotal * (rec.vat_rate / 100.0)
            rec.total_amount = rec.subtotal + rec.vat_amount

    @api.depends("total_amount")
    def _compute_director_required(self):
        for rec in self:
            rec.director_required = rec.total_amount > rec.DIRECTOR_THRESHOLD

    @api.depends("grn_ids")
    def _compute_grn_count(self):
        for rec in self:
            rec.grn_count = len(rec.grn_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.po") or _("New")
        return super().create(vals_list)

    def action_qs_approve(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft POs can be QS-approved."))
            if not rec.line_ids:
                raise UserError(_("Add lines before approving."))
            rec.write({
                "state": "qs_approved",
                "qs_approved_by": self.env.user.id,
                "qs_approved_date": fields.Datetime.now(),
            })

    def action_pm_approve(self):
        for rec in self:
            if rec.state != "qs_approved":
                raise UserError(_(
                    "PO must be QS-approved before PM approval."))
            new_state = "approved" if not rec.director_required else "pm_approved"
            rec.write({
                "state": new_state,
                "pm_approved_by": self.env.user.id,
                "pm_approved_date": fields.Datetime.now(),
            })

    def action_director_approve(self):
        for rec in self:
            if rec.state != "pm_approved":
                raise UserError(_(
                    "PO must be PM-approved first."))
            if not rec.director_required:
                raise UserError(_(
                    "This PO does not require Director approval."))
            rec.write({
                "state": "approved",
                "director_approved_by": self.env.user.id,
                "director_approved_date": fields.Datetime.now(),
            })

    def action_issue(self):
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("PO must be fully approved before issuing."))
            rec.state = "issued"

    def action_create_grn(self):
        """Create a GRN to receive goods from this PO."""
        self.ensure_one()
        if self.state not in ("issued", "partial"):
            raise UserError(_(
                "GRN can only be raised against an issued PO."))
        grn = self.env["buruuj.grn"].create({
            "po_id": self.id,
            "project_id": self.project_id.id,
            "vendor_id": self.vendor_id.id,
        })
        # Copy outstanding line quantities
        for pl in self.line_ids:
            outstanding = pl.quantity - pl.received_qty
            if outstanding > 0:
                self.env["buruuj.grn.line"].create({
                    "grn_id": grn.id,
                    "po_line_id": pl.id,
                    "material_id": pl.material_id.id,
                    "uom_id": pl.uom_id.id,
                    "ordered_qty": pl.quantity,
                    "previously_received": pl.received_qty,
                    "received_qty": outstanding,
                    "unit_price": pl.unit_price,
                })
        return {
            "type": "ir.actions.act_window",
            "res_model": "buruuj.grn",
            "res_id": grn.id,
            "view_mode": "form",
        }

    def action_view_grns(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Goods Receipt Notes"),
            "res_model": "buruuj.grn",
            "view_mode": "list,form",
            "domain": [("po_id", "=", self.id)],
            "context": {"default_po_id": self.id},
        }

    def action_close(self):
        self.state = "closed"

    def action_cancel(self):
        for rec in self:
            if rec.state == "received":
                raise UserError(_("Cannot cancel a fully received PO."))
            rec.state = "cancelled"


class BuruujPOLine(models.Model):
    _name = "buruuj.po.line"
    _description = "Purchase Order Line"
    _order = "sequence, id"

    po_id = fields.Many2one("buruuj.po", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    material_id = fields.Many2one("buruuj.material", required=True)
    specification = fields.Char()
    quantity = fields.Float(string="Ordered Qty", required=True, default=1.0)
    uom_id = fields.Many2one("uom.uom", required=True)
    unit_price = fields.Monetary(required=True)
    line_total = fields.Monetary(compute="_compute_total", store=True)
    received_qty = fields.Float(string="Received Qty",
                                  compute="_compute_received", store=True)
    outstanding_qty = fields.Float(string="Outstanding",
                                     compute="_compute_received", store=True)
    notes = fields.Char()
    currency_id = fields.Many2one("res.currency",
                                    related="po_id.currency_id")

    @api.onchange("material_id")
    def _onchange_material(self):
        if self.material_id:
            self.uom_id = self.material_id.uom_id
            if not self.specification:
                self.specification = self.material_id.specification
            if self.material_id.last_purchase_price and not self.unit_price:
                self.unit_price = self.material_id.last_purchase_price

    @api.depends("quantity", "unit_price")
    def _compute_total(self):
        for rec in self:
            rec.line_total = rec.quantity * rec.unit_price

    @api.depends("po_id.grn_ids.state",
                 "po_id.grn_ids.line_ids.received_qty",
                 "po_id.grn_ids.line_ids.po_line_id")
    def _compute_received(self):
        for rec in self:
            received = 0.0
            for grn in rec.po_id.grn_ids.filtered(
                    lambda g: g.state in ("accepted", "partial")):
                for gl in grn.line_ids.filtered(lambda l: l.po_line_id == rec):
                    received += gl.accepted_qty
            rec.received_qty = received
            rec.outstanding_qty = rec.quantity - received
