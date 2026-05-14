# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujGRN(models.Model):
    """Goods Receipt Note — quality check on receipt."""
    _name = "buruuj.grn"
    _description = "Goods Receipt Note"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(copy=False, default=lambda s: _("New"), tracking=True)
    po_id = fields.Many2one("buruuj.po", required=True, tracking=True,
                              ondelete="restrict")
    project_id = fields.Many2one(related="po_id.project_id", store=True)
    vendor_id = fields.Many2one(related="po_id.vendor_id", store=True)

    date = fields.Date(default=fields.Date.context_today, required=True,
                         tracking=True)
    delivery_note_ref = fields.Char(string="Vendor Delivery Note Ref.")
    delivery_vehicle = fields.Char(string="Vehicle / Plate No.")
    received_by = fields.Many2one("res.users",
                                    default=lambda s: s.env.user,
                                    tracking=True)
    inspected_by = fields.Many2one("res.users",
                                     string="Quality Inspected By",
                                     tracking=True)
    inspection_date = fields.Date()

    line_ids = fields.One2many("buruuj.grn.line", "grn_id")
    has_rejection = fields.Boolean(compute="_compute_has_rejection",
                                     store=True)
    has_short_supply = fields.Boolean(compute="_compute_has_short_supply",
                                        store=True)
    overall_quality = fields.Selection([
        ("accepted", "Accepted"),
        ("conditional", "Accepted with Conditions"),
        ("partial_reject", "Partial Rejection"),
        ("full_reject", "Full Rejection"),
    ], tracking=True)
    quality_notes = fields.Text()

    state = fields.Selection([
        ("draft", "Draft"),
        ("inspected", "Inspected"),
        ("accepted", "Accepted - Stocked"),
        ("partial", "Partially Accepted"),
        ("rejected", "Rejected"),
    ], default="draft", tracking=True)

    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    @api.depends("line_ids.rejected_qty")
    def _compute_has_rejection(self):
        for rec in self:
            rec.has_rejection = any(
                ln.rejected_qty > 0 for ln in rec.line_ids)

    @api.depends("line_ids.received_qty", "line_ids.ordered_qty",
                 "line_ids.previously_received")
    def _compute_has_short_supply(self):
        for rec in self:
            short = False
            for ln in rec.line_ids:
                if ln.received_qty + ln.previously_received < ln.ordered_qty:
                    short = True
                    break
            rec.has_short_supply = short

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.grn") or _("New")
        return super().create(vals_list)

    def action_inspect(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("GRN has no lines."))
            rec.write({
                "state": "inspected",
                "inspected_by": self.env.user.id,
                "inspection_date": fields.Date.context_today(self),
            })

    def action_accept(self):
        for rec in self:
            if not rec.overall_quality:
                raise UserError(_(
                    "Set the overall quality decision before accepting."))
            # Decide accepted vs partial vs rejected
            if rec.overall_quality == "full_reject":
                rec.state = "rejected"
            elif rec.has_rejection:
                rec.state = "partial"
            else:
                rec.state = "accepted"
            # Update PO state
            rec._update_po_state()
            # Create stock movements
            rec._create_stock_movements()
            # Update last purchase price
            for ln in rec.line_ids.filtered(lambda l: l.accepted_qty > 0):
                if ln.material_id:
                    ln.material_id.last_purchase_price = ln.unit_price

    def _update_po_state(self):
        for rec in self:
            po = rec.po_id
            if not po:
                continue
            all_received = all(
                ln.outstanding_qty <= 0 for ln in po.line_ids)
            any_received = any(
                ln.received_qty > 0 for ln in po.line_ids)
            if all_received:
                po.state = "received"
            elif any_received:
                po.state = "partial"

    def _create_stock_movements(self):
        """Increase project stock for accepted quantities."""
        Stock = self.env["buruuj.stock.balance"]
        for rec in self:
            for ln in rec.line_ids.filtered(lambda l: l.accepted_qty > 0):
                Stock._adjust(
                    project_id=rec.project_id.id,
                    material_id=ln.material_id.id,
                    qty_delta=ln.accepted_qty,
                    movement_type="in",
                    ref=f"GRN {rec.name}",
                )


class BuruujGRNLine(models.Model):
    _name = "buruuj.grn.line"
    _description = "GRN Line"
    _order = "id"

    grn_id = fields.Many2one("buruuj.grn", required=True, ondelete="cascade")
    po_line_id = fields.Many2one("buruuj.po.line",
                                    string="Source PO Line",
                                    ondelete="restrict")
    material_id = fields.Many2one("buruuj.material", required=True)
    uom_id = fields.Many2one("uom.uom", required=True)
    ordered_qty = fields.Float(string="Total PO Qty", readonly=True)
    previously_received = fields.Float(readonly=True)
    received_qty = fields.Float(string="Received Qty (this GRN)",
                                  required=True, default=0.0)
    accepted_qty = fields.Float(string="Accepted Qty", default=0.0)
    rejected_qty = fields.Float(string="Rejected Qty",
                                  compute="_compute_rejected", store=True)
    rejection_reason = fields.Char()
    unit_price = fields.Monetary(readonly=True)
    accepted_value = fields.Monetary(compute="_compute_accepted_value",
                                       store=True)
    notes = fields.Char()
    currency_id = fields.Many2one("res.currency",
                                    related="grn_id.company_id.currency_id")

    @api.onchange("received_qty")
    def _onchange_received(self):
        if self.received_qty and not self.accepted_qty:
            self.accepted_qty = self.received_qty

    @api.depends("received_qty", "accepted_qty")
    def _compute_rejected(self):
        for rec in self:
            rec.rejected_qty = max(0.0, rec.received_qty - rec.accepted_qty)

    @api.depends("accepted_qty", "unit_price")
    def _compute_accepted_value(self):
        for rec in self:
            rec.accepted_value = rec.accepted_qty * rec.unit_price
