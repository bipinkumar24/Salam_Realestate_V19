# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request
# from odoo.addons.http_routing.models.ir_http import slug, unslug_url
from odoo.addons.http_routing.models.ir_qweb import IrQweb


class ir_qweb(IrQweb):

    def _prepare_environment(self, values):
        irQweb = super(IrQweb, self)._prepare_environment(values)
        values['slug'] = self.env['ir.http']._slug
        values['unslug_url'] = self.env['ir.http']._unslug_url

        if (not irQweb.env.context.get('minimal_qcontext') and
                request and hasattr(request, 'is_frontend') and request.is_frontend):
            return irQweb._prepare_frontend_environment(values)

        return irQweb


IrQweb._prepare_environment = ir_qweb._prepare_environment