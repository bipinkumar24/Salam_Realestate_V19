# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujRFQ(models.Model):
    """Request for Quotation issued to multiple vendors."""
    _name = "buruuj.rfq"
    _description = "Request for Quotation"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(copy=False, default=lambda s: _("New"), tracking=True)
    mr_id = fields.Many2one("buruuj.material.requisition",
                              string="Source MR", tracking=True)
    project_id = fields.Many2one("project.project", required=True,
                                   tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    response_due = fields.Date(string="Response Due By")

    line_ids = fields.One2many("buruuj.rfq.line", "rfq_id",
                                  string="Materials")
    quote_ids = fields.One2many("buruuj.rfq.quote", "rfq_id",
                                  string="Vendor Quotes")
    quote_count = fields.Integer(compute="_compute_quote_count")
    selected_quote_id = fields.Many2one("buruuj.rfq.quote",
                                          string="Selected Quote",
                                          tracking=True)

    notes = fields.Html()

    state = fields.Selection([
        ("draft", "Draft"),
        ("issued", "Issued to Vendors"),
        ("evaluating", "Quotes Received - Evaluating"),
        ("selected", "Vendor Selected"),
        ("po_raised", "PO Raised"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)

    @api.depends("quote_ids")
    def _compute_quote_count(self):
        for rec in self:
            rec.quote_count = len(rec.quote_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.rfq") or _("New")
        return super().create(vals_list)

    def action_issue(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Add materials before issuing the RFQ."))
            rec.state = "issued"

    def action_evaluate(self):
        for rec in self:
            if not rec.quote_ids:
                raise UserError(_(
                    "Capture at least one vendor quote before evaluating."))
            rec.state = "evaluating"

    def action_select_vendor(self):
        for rec in self:
            if not rec.selected_quote_id:
                raise UserError(_(
                    "Pick the winning quote before confirming selection."))
            rec.state = "selected"

    def action_raise_po(self):
        """Generate a PO from the selected quote."""
        self.ensure_one()
        if not self.selected_quote_id:
            raise UserError(_("Select a winning vendor quote first."))
        quote = self.selected_quote_id
        po = self.env["buruuj.po"].create({
            "rfq_id": self.id,
            "mr_id": self.mr_id.id if self.mr_id else False,
            "project_id": self.project_id.id,
            "vendor_id": quote.vendor_id.id,
            "delivery_terms": quote.delivery_terms,
            "payment_terms": quote.payment_terms,
        })
        for ql in quote.line_ids:
            self.env["buruuj.po.line"].create({
                "po_id": po.id,
                "material_id": ql.rfq_line_id.material_id.id,
                "specification": ql.rfq_line_id.specification,
                "quantity": ql.rfq_line_id.quantity,
                "uom_id": ql.rfq_line_id.uom_id.id,
                "unit_price": ql.unit_price,
            })
        self.state = "po_raised"
        if self.mr_id:
            self.mr_id.state = "po_raised"
        return {
            "type": "ir.actions.act_window",
            "res_model": "buruuj.po",
            "res_id": po.id,
            "view_mode": "form",
        }

    def action_cancel(self):
        self.state = "cancelled"


class BuruujRFQLine(models.Model):
    _name = "buruuj.rfq.line"
    _description = "RFQ Line"
    _order = "sequence, id"

    rfq_id = fields.Many2one("buruuj.rfq", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    material_id = fields.Many2one("buruuj.material", required=True)
    specification = fields.Char()
    quantity = fields.Float(required=True, default=1.0)
    uom_id = fields.Many2one("uom.uom", required=True)
    notes = fields.Char()


class BuruujRFQQuote(models.Model):
    """One row per vendor responding to the RFQ. Lines hold per-item prices."""
    _name = "buruuj.rfq.quote"
    _description = "Vendor Quote"
    _order = "total_amount asc"

    rfq_id = fields.Many2one("buruuj.rfq", required=True, ondelete="cascade")
    vendor_id = fields.Many2one(
        "res.partner", string="Vendor", required=True,
        domain=[("supplier_rank", ">", 0)])
    quote_ref = fields.Char(string="Vendor Reference")
    quote_date = fields.Date(default=fields.Date.context_today)
    validity_date = fields.Date(string="Quote Valid Until")
    delivery_terms = fields.Char()
    payment_terms = fields.Char()
    lead_time_days = fields.Integer(string="Lead Time (Days)")

    line_ids = fields.One2many("buruuj.rfq.quote.line", "quote_id")
    total_amount = fields.Monetary(compute="_compute_total", store=True)
    is_selected = fields.Boolean(compute="_compute_is_selected", store=True)
    notes = fields.Text()

    currency_id = fields.Many2one(
        "res.currency", related="rfq_id.currency_id")

    @api.depends("line_ids.line_total")
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped("line_total"))

    @api.depends("rfq_id.selected_quote_id")
    def _compute_is_selected(self):
        for rec in self:
            rec.is_selected = (rec.rfq_id.selected_quote_id == rec)


class BuruujRFQQuoteLine(models.Model):
    _name = "buruuj.rfq.quote.line"
    _description = "Vendor Quote Line"

    quote_id = fields.Many2one("buruuj.rfq.quote", required=True,
                                  ondelete="cascade")
    rfq_line_id = fields.Many2one("buruuj.rfq.line", required=True,
                                     string="RFQ Line")
    material_id = fields.Many2one(related="rfq_line_id.material_id",
                                     store=True)
    quantity = fields.Float(related="rfq_line_id.quantity", store=True)
    uom_id = fields.Many2one(related="rfq_line_id.uom_id", store=True)
    unit_price = fields.Monetary(required=True)
    line_total = fields.Monetary(compute="_compute_total", store=True)
    notes = fields.Char()

    currency_id = fields.Many2one(
        "res.currency", related="quote_id.currency_id")

    @api.depends("quantity", "unit_price")
    def _compute_total(self):
        for rec in self:
            rec.line_total = rec.quantity * rec.unit_price
