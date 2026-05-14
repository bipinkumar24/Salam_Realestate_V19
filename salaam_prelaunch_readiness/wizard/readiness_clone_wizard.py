# -*- coding: utf-8 -*-
"""
Tracker Clone Wizard - scaffold a new (Phase, Lot) tracker by copying
the structure of an existing one. Used to extend the platform from
Phase-1 Lot-1 to Phase-1 Lot-2, Phase-2 Lot-1, etc.

Copies the 14 categories with their gate type / sequence / required
threshold, and the 110 items with their names / sequence / category
binding. All status / owner / due / evidence fields reset.
"""
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReadinessCloneWizard(models.TransientModel):
    _name = "salaam.readiness.clone.wizard"
    _description = "Salaam Readiness - Tracker Clone Wizard"

    source_tracker_id = fields.Many2one(
        "salaam.readiness.tracker",
        string="Source Tracker",
        required=True,
        help="The tracker whose 14 categories and 110 items will be "
             "copied into a new tracker.",
    )
    new_name = fields.Char(
        string="New Tracker Name",
        required=True,
    )
    new_phase_label = fields.Char(string="Phase", required=True)
    new_lot_label = fields.Char(string="Lot", required=True)
    copy_due_dates = fields.Boolean(
        string="Copy Due Dates",
        default=False,
        help="If unticked (default), the new items have no due date and "
             "must be re-baselined for the new Phase/Lot timeline.",
    )

    @api.onchange("source_tracker_id", "new_phase_label", "new_lot_label")
    def _onchange_default_name(self):
        for rec in self:
            if rec.source_tracker_id and rec.new_phase_label and rec.new_lot_label:
                rec.new_name = "%s %s Pre-Launch Readiness" % (
                    rec.new_phase_label, rec.new_lot_label,
                )

    def action_clone(self):
        self.ensure_one()
        if not self.source_tracker_id:
            raise UserError(_("Please pick a source tracker."))

        Tracker = self.env["salaam.readiness.tracker"]
        Category = self.env["salaam.readiness.category"]
        Item = self.env["salaam.readiness.item"]

        src = self.source_tracker_id

        # 1. New tracker - draft state, no decision gate ref yet
        new_tracker = Tracker.create({
            "name": self.new_name,
            "phase_label": self.new_phase_label,
            "lot_label": self.new_lot_label,
            "state": "draft",
            "company_id": src.company_id.id,
        })

        # 2. Replicate all categories and build a code -> new_category map
        code_to_new_cat = {}
        for src_cat in src.category_ids.sorted(lambda c: (c.sequence, c.code)):
            new_cat = Category.create({
                "tracker_id": new_tracker.id,
                "code": src_cat.code,
                "name": src_cat.name,
                "gate_type": src_cat.gate_type,
                "sequence": src_cat.sequence,
            })
            code_to_new_cat[src_cat.code] = new_cat

        # 3. Replicate items - reset status, % complete, owner, evidence,
        #    linked record. Optionally copy due dates.
        item_vals = []
        for src_item in src.item_ids.sorted(lambda i: (i.category_code, i.sequence)):
            target_cat = code_to_new_cat.get(src_item.category_code)
            if not target_cat:
                continue
            vals = {
                "category_id": target_cat.id,
                "sequence": src_item.sequence,
                "name": src_item.name,
                "status": "not_started",
                "pct_complete": 0.0,
            }
            if self.copy_due_dates and src_item.due_date:
                vals["due_date"] = src_item.due_date
            item_vals.append(vals)
        if item_vals:
            Item.create(item_vals)

        new_tracker.message_post(
            body=_("Cloned from <b>%(src)s</b> by %(user)s. "
                   "%(cats)d categories and %(items)d items replicated.") % {
                "src": src.display_name,
                "user": self.env.user.display_name,
                "cats": len(code_to_new_cat),
                "items": len(item_vals),
            },
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("New Tracker"),
            "res_model": "salaam.readiness.tracker",
            "res_id": new_tracker.id,
            "view_mode": "form",
            "target": "current",
        }
