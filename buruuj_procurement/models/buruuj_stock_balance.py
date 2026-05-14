# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class BuruujStockBalance(models.Model):
    """Real-time stock balance: one row per (project, material).

    Movements are tracked in buruuj.stock.movement; this is the rolled-up view.
    """
    _name = "buruuj.stock.balance"
    _description = "Project Stock Balance"
    _order = "project_id, material_id"

    project_id = fields.Many2one("project.project", required=True,
                                   ondelete="cascade")
    material_id = fields.Many2one("buruuj.material", required=True,
                                    ondelete="restrict")
    quantity = fields.Float(string="On-Hand Qty", default=0.0)
    uom_id = fields.Many2one(related="material_id.uom_id", store=True)
    last_movement_date = fields.Datetime(readonly=True)
    movement_ids = fields.One2many("buruuj.stock.movement",
                                      "balance_id")

    company_id = fields.Many2one("res.company",
                                   default=lambda s: s.env.company)

    _sql_constraints = [
        ("project_material_unique",
         "unique(project_id, material_id, company_id)",
         "Only one stock balance row per project per material."),
    ]

    @api.model
    def _get_balance(self, project_id, material_id):
        """Convenience: return current balance or 0 if no row yet."""
        rec = self.search([
            ("project_id", "=", project_id),
            ("material_id", "=", material_id),
        ], limit=1)
        return rec.quantity if rec else 0.0

    @api.model
    def _adjust(self, project_id, material_id, qty_delta,
                movement_type="adjust", ref=""):
        """Apply a stock movement. Creates a balance row if needed."""
        bal = self.search([
            ("project_id", "=", project_id),
            ("material_id", "=", material_id),
        ], limit=1)
        if not bal:
            bal = self.create({
                "project_id": project_id,
                "material_id": material_id,
                "quantity": 0.0,
            })
        bal.quantity += qty_delta
        bal.last_movement_date = fields.Datetime.now()
        # Audit trail
        self.env["buruuj.stock.movement"].create({
            "balance_id": bal.id,
            "project_id": project_id,
            "material_id": material_id,
            "movement_type": movement_type,
            "qty": qty_delta,
            "reference": ref,
            "user_id": self.env.user.id,
        })
        return bal


class BuruujStockMovement(models.Model):
    """Audit trail of every stock change."""
    _name = "buruuj.stock.movement"
    _description = "Stock Movement"
    _order = "date desc, id desc"

    balance_id = fields.Many2one("buruuj.stock.balance",
                                    ondelete="set null")
    project_id = fields.Many2one("project.project", required=True)
    material_id = fields.Many2one("buruuj.material", required=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True)
    movement_type = fields.Selection([
        ("in", "Goods Received"),
        ("out", "Issued to Work"),
        ("transfer_in", "Transfer In"),
        ("transfer_out", "Transfer Out"),
        ("adjust", "Adjustment"),
        ("return", "Return"),
    ], required=True)
    qty = fields.Float(string="Qty Delta",
                         help="Positive = stock added; negative = stock removed.")
    reference = fields.Char(string="Source Reference")
    user_id = fields.Many2one("res.users", readonly=True)
    notes = fields.Char()
