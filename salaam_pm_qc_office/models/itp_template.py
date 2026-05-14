from odoo import fields, models


class ItpTemplate(models.Model):
    _name = "salaam.pm.qc.itp.template"
    _description = "ITP / ITR Template"
    _order = "code, id"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(required=True, tracking=True)
    template_type = fields.Selection(
        [
            ("itp", "Inspection & Test Plan"),
            ("itr", "Inspection & Test Report"),
        ],
        required=True,
        default="itp",
        tracking=True,
    )
    discipline = fields.Selection(
        [
            ("civil", "Civil"),
            ("structural", "Structural"),
            ("mep", "MEP"),
            ("hse", "HSE"),
            ("other", "Other"),
        ],
        default="civil",
        tracking=True,
    )
    description = fields.Html()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, required=True
    )

    _sql_constraints = [
        ("uniq_code_company", "unique(code, company_id)",
         "ITP/ITR code must be unique per company."),
    ]
