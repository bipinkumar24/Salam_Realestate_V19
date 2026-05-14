# -*- coding: utf-8 -*-
from odoo import models, fields


class DevContractClause(models.Model):
    _name = 'dev.contract.clause'
    _description = 'Contract Clause Library'
    _order = 'clause_code'

    name = fields.Char(string='Clause Title', required=True)
    clause_code = fields.Char(
        string='Clause Code', required=True, copy=False,
        help='Unique code e.g. CL-FM-001',
    )
    content = fields.Html(string='Clause Text', required=True)
    contract_types = fields.Many2many(
        'dev.contract.clause.type', string='Applicable Contract Types',
    )
    sharia_applicable = fields.Boolean(
        string='Sharia Specific',
        help='Clause is specific to Sharia-compliant contracts',
    )
    is_mandatory = fields.Boolean(
        string='Mandatory',
        help='Auto-attached to all contracts of the applicable type and cannot be removed',
    )
    active = fields.Boolean(default=True)


class DevContractClauseType(models.Model):
    """Simple tag model so clauses can be tagged by contract type."""
    _name = 'dev.contract.clause.type'
    _description = 'Contract Clause Type Tag'

    name = fields.Char(string='Type', required=True)
