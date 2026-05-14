# -*- coding: utf-8 -*-
from odoo import models, fields, _
from odoo.exceptions import UserError


class BoqImportWizard(models.TransientModel):
    _name = 'boq.import.wizard'
    _description = 'Bulk Import BOQ Drawings'

    partner_id = fields.Many2one('res.partner', string='Customer')
    project_id = fields.Many2one('project.project', string='Project')
    auto_analyze = fields.Boolean(default=True,
        help="If checked, each upload is analysed by the AI immediately.")
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Drawings',
        help="Upload one or more PDF/PNG/JPG files. One BOQ project will be created per file.")

    def action_import(self):
        self.ensure_one()
        if not self.attachment_ids:
            raise UserError(_("Attach at least one drawing."))
        Project = self.env['ai.boq.project']
        created = self.env['ai.boq.project']
        for att in self.attachment_ids:
            vals = {
                'name': _('New'),
                'partner_id': self.partner_id.id,
                'project_id': self.project_id.id,
                'design_file': att.datas,
                'design_filename': att.name,
            }
            rec = Project.create(vals)
            created |= rec
            if self.auto_analyze:
                try:
                    rec.action_analyze()
                except Exception as e:
                    rec.message_post(body=_("Auto-analysis failed: %s") % e)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Imported BOQs'),
            'res_model': 'ai.boq.project',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created.ids)],
        }
