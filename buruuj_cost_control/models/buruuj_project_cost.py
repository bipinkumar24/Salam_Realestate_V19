# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ProjectProject(models.Model):
    _inherit = "project.project"

    cbs_ids = fields.One2many("buruuj.cbs", "project_id", string="CBS Lines")
    cbs_count = fields.Integer(compute="_compute_cbs_count")
    cost_entry_ids = fields.One2many("buruuj.cost.entry", "project_id",
                                       string="Cost Entries")
    variance_ids = fields.One2many("buruuj.variance", "project_id",
                                     string="Variance Log")

    # Project P&L
    pnl_total_baseline = fields.Monetary(compute="_compute_pnl", store=False)
    pnl_total_revised = fields.Monetary(compute="_compute_pnl", store=False)
    pnl_total_committed = fields.Monetary(compute="_compute_pnl", store=False)
    pnl_total_actual = fields.Monetary(compute="_compute_pnl", store=False)
    pnl_total_etc = fields.Monetary(compute="_compute_pnl", store=False)
    pnl_total_fac = fields.Monetary(compute="_compute_pnl", store=False)
    pnl_total_vac = fields.Monetary(compute="_compute_pnl", store=False)

    # Earned value snapshots
    pnl_bcws = fields.Monetary(compute="_compute_evm",
                                  string="BCWS (Planned Value)",
                                  help="Budgeted Cost of Work Scheduled")
    pnl_bcwp = fields.Monetary(compute="_compute_evm",
                                  string="BCWP (Earned Value)",
                                  help="Budgeted Cost of Work Performed")
    pnl_acwp = fields.Monetary(compute="_compute_evm",
                                  string="ACWP (Actual Cost)",
                                  help="Actual Cost of Work Performed")
    pnl_cv = fields.Monetary(compute="_compute_evm",
                                string="Cost Variance (CV)",
                                help="BCWP - ACWP. Negative = overrun.")
    pnl_sv = fields.Monetary(compute="_compute_evm",
                                string="Schedule Variance (SV)",
                                help="BCWP - BCWS. Negative = behind schedule.")
    pnl_cpi = fields.Float(compute="_compute_evm", string="CPI",
                              help="Cost Performance Index = BCWP / ACWP. >1 = under budget.")
    pnl_spi = fields.Float(compute="_compute_evm", string="SPI",
                              help="Schedule Performance Index = BCWP / BCWS. >1 = ahead.")

    # Margin
    pnl_margin_baseline = fields.Monetary(compute="_compute_pnl",
                                              string="Baseline Margin")
    pnl_margin_forecast = fields.Monetary(compute="_compute_pnl",
                                              string="Forecast Margin")
    pnl_margin_movement = fields.Monetary(compute="_compute_pnl",
                                              string="Margin Movement",
                                              help="Forecast margin minus baseline margin.")

    @api.depends("cbs_ids")
    def _compute_cbs_count(self):
        for rec in self:
            rec.cbs_count = len(rec.cbs_ids)

    @api.depends("cbs_ids.rollup_baseline", "cbs_ids.rollup_revised",
                 "cbs_ids.rollup_committed", "cbs_ids.rollup_actual",
                 "cbs_ids.rollup_etc", "cbs_ids.rollup_fac",
                 "cbs_ids.parent_id", "buruuj_contract_value")
    def _compute_pnl(self):
        for rec in self:
            top = rec.cbs_ids.filtered(lambda c: not c.parent_id)
            rec.pnl_total_baseline = sum(top.mapped("rollup_baseline"))
            rec.pnl_total_revised = sum(top.mapped("rollup_revised"))
            rec.pnl_total_committed = sum(top.mapped("rollup_committed"))
            rec.pnl_total_actual = sum(top.mapped("rollup_actual"))
            rec.pnl_total_etc = sum(top.mapped("rollup_etc"))
            rec.pnl_total_fac = sum(top.mapped("rollup_fac"))
            rec.pnl_total_vac = rec.pnl_total_revised - rec.pnl_total_fac
            # Margin
            rec.pnl_margin_baseline = (rec.buruuj_contract_value or 0.0) - rec.pnl_total_baseline
            rec.pnl_margin_forecast = (rec.buruuj_contract_value or 0.0) - rec.pnl_total_fac
            rec.pnl_margin_movement = rec.pnl_margin_forecast - rec.pnl_margin_baseline

    @api.depends("cbs_ids.physical_progress", "cbs_ids.rollup_baseline",
                 "cbs_ids.rollup_actual", "cbs_ids.parent_id")
    def _compute_evm(self):
        for rec in self:
            # BCWP = sum across CBS leaves of (physical_progress% * baseline)
            # BCWS = sum of baseline planned to be earned by today (we use
            #   simplified approach: leaves with start_date <= today contribute
            #   their full baseline; this is rough but adequate for a UI metric)
            # ACWP = total actuals
            leaves = rec.cbs_ids.filtered(lambda c: c.is_leaf)
            bcwp = sum((leaf.physical_progress or 0.0) / 100.0
                          * leaf.baseline_budget for leaf in leaves)
            acwp = sum(leaves.mapped("actual_amount"))
            # BCWS — simplified: same as BCWP if no time-phasing data.
            # Time-phased version comes from the time-phasing model.
            tp_total = sum(rec.env["buruuj.time.phasing"].search([
                ("project_id", "=", rec.id),
                ("date", "<=", fields.Date.context_today(rec)),
            ]).mapped("planned_amount"))
            bcws = tp_total if tp_total else bcwp
            rec.pnl_bcws = bcws
            rec.pnl_bcwp = bcwp
            rec.pnl_acwp = acwp
            rec.pnl_cv = bcwp - acwp
            rec.pnl_sv = bcwp - bcws
            rec.pnl_cpi = (bcwp / acwp) if acwp else 0.0
            rec.pnl_spi = (bcwp / bcws) if bcws else 0.0

    def action_view_pnl(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Project P&L"),
            "res_model": "buruuj.cbs",
            "view_mode": "list,form",
            "domain": [("project_id", "=", self.id),
                         ("parent_id", "=", False)],
            "context": {"default_project_id": self.id,
                          "search_default_g_cat": 1},
        }

    def action_refresh_costs(self):
        """Manually rebuild all auto cost entries for this project from the
        source documents. Useful after config changes or imports."""
        self.ensure_one()
        Builder = self.env["buruuj.cost.entry"]
        # Subcontracts: contract value as committed (signed)
        for sub in self.env["buruuj.subcontract"].search([
                ("project_id", "=", self.id),
                ("state", "in", ["signed", "in_progress",
                                   "practically_complete", "in_dlp"]),
        ]):
            # Find the "Subcontract" CBS for this trade if any, else first SC line
            cbs = self.cbs_ids.filtered(
                lambda c: c.cost_type == "subcontract" and c.is_leaf)[:1]
            if cbs:
                Builder._record_from_source(
                    sub, cbs.id, "committed", sub.contract_value,
                    name=f"Subcontract: {sub.title or sub.name}",
                    ref=sub.name)

        # Subcontractor IPCs: net amount as actual
        for ipc in self.env["buruuj.ipc"].search([
                ("project_id", "=", self.id),
                ("type", "=", "subcontractor"),
                ("state", "=", "paid"),
        ]):
            cbs = self.cbs_ids.filtered(
                lambda c: c.cost_type == "subcontract" and c.is_leaf)[:1]
            if cbs:
                Builder._record_from_source(
                    ipc, cbs.id, "actual", ipc.net_amount,
                    name=f"Sub IPC #{ipc.sequence_no}",
                    ref=ipc.name, date=ipc.period_to)

        # Procurement POs: total as committed
        for po in self.env["buruuj.po"].search([
                ("project_id", "=", self.id),
                ("state", "in", ["issued", "partial", "received"]),
        ]):
            cbs = self.cbs_ids.filtered(
                lambda c: c.cost_type == "direct_material" and c.is_leaf)[:1]
            if cbs:
                Builder._record_from_source(
                    po, cbs.id, "committed", po.total_amount,
                    name=f"PO: {po.vendor_id.name}",
                    ref=po.name)

        # Material issuances: total value as actual
        for iss in self.env["buruuj.material.issuance"].search([
                ("project_id", "=", self.id),
                ("state", "=", "issued"),
        ]):
            cbs = self.cbs_ids.filtered(
                lambda c: c.cost_type == "direct_material" and c.is_leaf)[:1]
            if cbs:
                Builder._record_from_source(
                    iss, cbs.id, "actual", iss.total_value,
                    name=f"Issued: {iss.name}",
                    ref=iss.name, date=iss.date)

        # Rental contracts: estimated cost as committed
        for rc in self.env["buruuj.rental.contract"].search([
                ("project_id", "=", self.id),
                ("state", "in", ["active", "off_hire_pending",
                                   "off_hired", "closed"]),
        ]):
            cbs = self.cbs_ids.filtered(
                lambda c: c.cost_type == "rental" and c.is_leaf)[:1]
            if cbs:
                Builder._record_from_source(
                    rc, cbs.id, "committed", rc.estimated_cost,
                    name=f"Rental: {rc.equipment_description}",
                    ref=rc.name)
                if rc.invoiced_amount:
                    Builder._record_from_source(
                        rc, cbs.id, "actual", rc.invoiced_amount,
                        name=f"Rental paid: {rc.equipment_description}",
                        ref=f"{rc.name} (invoices)")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Costs Refreshed"),
                "message": _("Cost entries rebuilt from source documents."),
                "type": "success",
            },
        }
