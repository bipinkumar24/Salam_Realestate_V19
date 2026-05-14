# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class BuruujPortalMain(CustomerPortal):
    """Extends Odoo portal home with Buruuj-specific counters."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if not partner:
            return values
        # Inject Buruuj counts
        try:
            buruuj_counts = partner._portal_get_counts()
        except Exception:
            buruuj_counts = {}

        if "projects_count" in counters:
            values["projects_count"] = buruuj_counts.get("projects", 0)
        if "ipcs_count" in counters:
            values["ipcs_count"] = buruuj_counts.get("client_ipcs", 0)
        if "ipcs_pending_count" in counters:
            values["ipcs_pending_count"] = buruuj_counts.get("ipcs_pending", 0)
        if "rfis_count" in counters:
            values["rfis_count"] = buruuj_counts.get("rfis", 0)
        if "variations_count" in counters:
            values["variations_count"] = buruuj_counts.get("variations_pending", 0)
        if "drawings_count" in counters:
            values["drawings_count"] = buruuj_counts.get("drawings_pending", 0)
        if "subs_count" in counters:
            values["subs_count"] = buruuj_counts.get("subs", 0)
        if "wos_count" in counters:
            values["wos_count"] = buruuj_counts.get("wos_unack", 0)
        if "sub_ipcs_count" in counters:
            values["sub_ipcs_count"] = buruuj_counts.get("sub_ipcs", 0)
        if "backcharges_count" in counters:
            values["backcharges_count"] = buruuj_counts.get("backcharges_open", 0)
        return values
