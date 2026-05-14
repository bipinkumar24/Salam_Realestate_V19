# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BuruujCostEntry(models.Model):
    """A single line of cost — either a commitment or an actual.

    Most entries are auto-generated from the source documents (POs, IPCs,
    GRNs, work orders, rental contracts, plant allocations, back-charges).
    Manual entries are also allowed for indirect costs / overheads."""
    _name = "buruuj.cost.entry"
    _description = "Project Cost Entry"
    _inherit = ["mail.thread"]
    _order = "date desc, id desc"

    name = fields.Char(string="Description", required=True, tracking=True)
    cbs_id = fields.Many2one("buruuj.cbs", string="CBS Line", required=True,
                               ondelete="restrict", tracking=True)
    project_id = fields.Many2one(related="cbs_id.project_id", store=True,
                                   readonly=True)
    category_id = fields.Many2one(related="cbs_id.category_id", store=True)
    cost_type = fields.Selection(related="cbs_id.cost_type", store=True)

    date = fields.Date(default=fields.Date.context_today, required=True,
                         tracking=True)
    period_year = fields.Integer(compute="_compute_period", store=True)
    period_month = fields.Integer(compute="_compute_period", store=True)

    entry_type = fields.Selection([
        ("committed", "Committed"),
        ("actual", "Actual"),
    ], required=True, default="committed", tracking=True)
    amount = fields.Monetary(required=True, tracking=True)

    # Source linkage — polymorphic via model+id
    source_model = fields.Char(string="Source Model")
    source_id = fields.Integer(string="Source ID")
    source_ref = fields.Char(string="Source Reference",
                               help="Human-readable ref like PO/2026/0042 or IPC/3.")
    is_auto_generated = fields.Boolean(default=False, readonly=True,
                                          tracking=True)

    notes = fields.Text()
    currency_id = fields.Many2one(
        "res.currency",
        default=lambda s: s.env.company.currency_id, store=True)
    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    @api.depends("date")
    def _compute_period(self):
        for rec in self:
            if rec.date:
                rec.period_year = rec.date.year
                rec.period_month = rec.date.month
            else:
                rec.period_year = 0
                rec.period_month = 0

    def write(self, vals):
        # Prevent editing of auto-generated entries except by manager
        for rec in self:
            if rec.is_auto_generated and not self.env.user.has_group(
                    "buruuj_cost_control.group_buruuj_cost_officer"):
                non_editable = set(vals.keys()) - {"notes"}
                if non_editable:
                    raise UserError(_(
                        "Auto-generated entries cannot be edited directly. "
                        "Modify the source document instead. "
                        "(Cost Officers may edit notes only.)"))
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.is_auto_generated and not self.env.user.has_group(
                    "buruuj_cost_control.group_buruuj_cost_officer"):
                raise UserError(_(
                    "Auto-generated cost entries cannot be deleted directly. "
                    "Cancel the source document."))
        return super().unlink()

    def action_open_source(self):
        """Navigate to the source record, if any."""
        self.ensure_one()
        if not (self.source_model and self.source_id):
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.source_model,
            "res_id": self.source_id,
            "view_mode": "form",
        }

    @api.model
    def _record_from_source(self, source_record, cbs_id, entry_type, amount,
                             date=None, name=None, ref=None):
        """Helper to create or update a cost entry from a source record.

        Idempotent: if an entry already exists for the same source and type,
        it's updated instead of duplicated.
        """
        if not (source_record and cbs_id and amount):
            return False
        existing = self.search([
            ("source_model", "=", source_record._name),
            ("source_id", "=", source_record.id),
            ("entry_type", "=", entry_type),
            ("cbs_id", "=", cbs_id),
        ], limit=1)
        vals = {
            "name": name or f"{source_record._description}: {source_record.display_name}",
            "cbs_id": cbs_id,
            "entry_type": entry_type,
            "amount": amount,
            "date": date or fields.Date.context_today(self),
            "source_model": source_record._name,
            "source_id": source_record.id,
            "source_ref": ref or source_record.display_name,
            "is_auto_generated": True,
        }
        if existing:
            existing.write({"amount": amount, "date": vals["date"]})
            return existing
        return self.create(vals)
