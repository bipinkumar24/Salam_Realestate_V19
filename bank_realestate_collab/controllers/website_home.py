# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class BREWebsiteHome(http.Controller):
    """Override the website homepage with SRE real estate landing page."""

    @http.route('/', type='http', auth='public', website=True)
    def homepage(self, **kw):
        """Serve the SRE Real Estate homepage."""
        # Fetch a few available properties to show on the homepage
        properties = request.env['property.details'].sudo().search(
            [('stage', '=', 'available')],
            order='id desc', limit=6
        )
        return request.render('bank_realestate_collab.sre_homepage', {
            'properties': properties,
        })
