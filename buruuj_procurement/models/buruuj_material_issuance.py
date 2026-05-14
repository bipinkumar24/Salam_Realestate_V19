# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujMaterialIssuance(models.Model):
    """Material issuance from store to a work activity."""
    _name = "buruuj.material.issuance"
    _description = "Material Issuance"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(copy=False, default=lambda s: _("New"))
    project_id = fields.Many2one("project.project", required=True)
    phase_id = fields.Many2one("buruuj.phase",
                                 domain="[('project_id','=',project_id)]")
    boq_line_ref = fields.Char(string="BOQ Reference")
    subcontract_id = fields.Many2one(
        "buruuj.subcontract", string="Issued to Subcontract",
        domain="[('project_id','=',project_id)]",
        help="Optional. If set, the cost can be back-charged to this subcontractor.")
    date = fields.Date(default=fields.Date.context_today, required=True)
    issued_by = fields.Many2one("res.users",
                                  default=lambda s: s.env.user)
    received_by_name = fields.Char(string="Received By (Name on Site)")
    line_ids = fields.One2many("buruuj.material.issuance.line",
                                  "issuance_id")
    total_value = fields.Monetary(compute="_compute_total", store=True)
    purpose = fields.Text()

    state = fields.Selection([
        ("draft", "Draft"),
        ("issued", "Issued"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)

    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)
    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)

    @api.depends("line_ids.line_value")
    def _compute_total(self):
        for rec in self:
            rec.total_value = sum(rec.line_ids.mapped("line_value"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.material.issuance") or _("New")
        return super().create(vals_list)

    def action_issue(self):
        Stock = self.env["buruuj.stock.balance"]
        for rec in self:
            if not rec.line_ids:
                raise UserError(_("Add at least one line."))
            # Validate stock sufficiency
            for ln in rec.line_ids:
                bal = Stock._get_balance(rec.project_id.id, ln.material_id.id)
                if bal < ln.quantity:
                    raise UserError(_(
                        "Insufficient stock for %(mat)s on %(proj)s. "
                        "Available: %(bal)s; requested: %(req)s.",
                        mat=ln.material_id.display_name,
                        proj=rec.project_id.name,
                        bal=bal, req=ln.quantity,
                    ))
            for ln in rec.line_ids:
                Stock._adjust(
                    project_id=rec.project_id.id,
                    material_id=ln.material_id.id,
                    qty_delta=-ln.quantity,
                    movement_type="out",
                    ref=f"Issuance {rec.name}",
                )
            rec.state = "issued"

    def action_cancel(self):
        for rec in self:
            if rec.state == "issued":
                raise UserError(_(
                    "Cannot cancel an already-issued record. Raise a return instead."))
            rec.state = "cancelled"


class BuruujMaterialIssuanceLine(models.Model):
    _name = "buruuj.material.issuance.line"
    _description = "Material Issuance Line"

    issuance_id = fields.Many2one("buruuj.material.issuance",
                                     required=True, ondelete="cascade")
    material_id = fields.Many2one("buruuj.material", required=True)
    uom_id = fields.Many2one("uom.uom", required=True)
    quantity = fields.Float(required=True, default=1.0)
    unit_value = fields.Monetary(string="Unit Value")
    line_value = fields.Monetary(compute="_compute_value", store=True)
    notes = fields.Char()
    currency_id = fields.Many2one(
        "res.currency", related="issuance_id.currency_id")

    @api.onchange("material_id")
    def _onchange_material(self):
        if self.material_id:
            self.uom_id = self.material_id.uom_id
            if self.material_id.last_purchase_price and not self.unit_value:
                self.unit_value = self.material_id.last_purchase_price

    @api.depends("quantity", "unit_value")
    def _compute_value(self):
        for rec in self:
            rec.line_value = rec.quantity * rec.unit_value
