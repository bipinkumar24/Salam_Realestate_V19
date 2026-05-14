# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujRentalRequisition(models.Model):
    """Site Engineer requests rental equipment. Procurement actions it."""
    _name = "buruuj.rental.requisition"
    _description = "Rental Requisition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date desc, id desc"

    name = fields.Char(copy=False, default=lambda s: _("New"))
    project_id = fields.Many2one("project.project", required=True, tracking=True)
    requested_by = fields.Many2one(
        "res.users", default=lambda s: s.env.user, tracking=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    required_from = fields.Date(string="Required From", required=True, tracking=True)
    required_to = fields.Date(string="Required To", required=True)
    duration_days = fields.Integer(compute="_compute_duration", store=True)

    equipment_type = fields.Selection([
        ("excavator", "Excavator"),
        ("loader", "Loader / Backhoe"),
        ("crane_mobile", "Mobile Crane"),
        ("crane_tower", "Tower Crane"),
        ("dozer", "Bulldozer"),
        ("compactor", "Compactor / Roller"),
        ("dump_truck", "Dump Truck"),
        ("concrete_pump", "Concrete Pump"),
        ("scissor_lift", "Scissor / Boom Lift"),
        ("forklift", "Forklift"),
        ("generator", "Generator"),
        ("other", "Other"),
    ], required=True, tracking=True)
    capacity_required = fields.Char(
        string="Capacity / Specification",
        help="E.g., 25-ton crane, 20m³ excavator, 100kVA generator")
    quantity = fields.Integer(default=1, required=True)
    work_description = fields.Text(string="Intended Use", required=True)
    priority = fields.Selection([
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ], default="normal", tracking=True)

    estimated_cost = fields.Monetary(string="Estimated Cost",
                                       help="Rough budget guidance for procurement.")
    contract_ids = fields.One2many("buruuj.rental.contract", "requisition_id")
    contract_count = fields.Integer(compute="_compute_contract_count")

    state = fields.Selection([
        ("draft", "Draft"),
        ("submitted", "Submitted to Procurement"),
        ("quoting", "Procurement Quoting"),
        ("contracted", "Contract Issued"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ], default="draft", tracking=True)
    rejection_reason = fields.Text()

    currency_id = fields.Many2one(
        "res.currency", default=lambda s: s.env.company.currency_id)
    company_id = fields.Many2one("res.company", default=lambda s: s.env.company)

    @api.depends("required_from", "required_to")
    def _compute_duration(self):
        for rec in self:
            if rec.required_from and rec.required_to:
                rec.duration_days = (rec.required_to - rec.required_from).days + 1
            else:
                rec.duration_days = 0

    @api.depends("contract_ids")
    def _compute_contract_count(self):
        for rec in self:
            rec.contract_count = len(rec.contract_ids)

    @api.constrains("required_from", "required_to")
    def _check_dates(self):
        for rec in self:
            if rec.required_from and rec.required_to and rec.required_to < rec.required_from:
                raise UserError(_("Required-to date must be on or after required-from."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", _("New")) == _("New"):
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "buruuj.rental.requisition") or _("New")
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft requisitions can be submitted."))
            rec.state = "submitted"

    def action_start_quoting(self):
        self.state = "quoting"

    def action_reject(self):
        self.state = "rejected"

    def action_cancel(self):
        self.state = "cancelled"

    def action_view_contracts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Rental Contracts"),
            "res_model": "buruuj.rental.contract",
            "view_mode": "list,form",
            "domain": [("requisition_id", "=", self.id)],
            "context": {"default_requisition_id": self.id,
                          "default_project_id": self.project_id.id},
        }
