# -*- coding: utf-8 -*-
"""Routes the subcontractor uses to view their work and submit IPCs."""
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, UserError
from odoo.addons.portal.controllers.portal import CustomerPortal


class BuruujSubPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # SUBCONTRACTS
    # ------------------------------------------------------------------
    @http.route("/my/subcontracts", type="http", auth="user", website=True)
    def portal_subs(self, **kw):
        partner = request.env.user.partner_id
        subs = request.env["buruuj.subcontract"]._portal_get_for_partner(partner)
        return request.render("buruuj_portal.portal_my_subs", {
            "subs": subs,
            "page_name": "buruuj_subs",
        })

    @http.route("/my/subcontracts/<int:sub_id>", type="http", auth="user", website=True)
    def portal_sub_detail(self, sub_id, **kw):
        partner = request.env.user.partner_id
        sub = request.env["buruuj.subcontract"].sudo().browse(sub_id)
        if sub.partner_id != partner:
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_sub_detail", {
            "sub": sub,
            "page_name": "buruuj_subs",
        })

    # ------------------------------------------------------------------
    # WORK ORDERS
    # ------------------------------------------------------------------
    @http.route("/my/workorders", type="http", auth="user", website=True)
    def portal_wos(self, **kw):
        partner = request.env.user.partner_id
        wos = request.env["buruuj.workorder"]._portal_get_for_partner(partner)
        return request.render("buruuj_portal.portal_my_wos", {
            "wos": wos,
            "page_name": "buruuj_wos",
        })

    @http.route("/my/workorders/<int:wo_id>", type="http", auth="user", website=True)
    def portal_wo_detail(self, wo_id, **kw):
        partner = request.env.user.partner_id
        wo = request.env["buruuj.workorder"].sudo().browse(wo_id)
        if wo.subcontract_id.partner_id != partner:
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_wo_detail", {
            "wo": wo,
            "page_name": "buruuj_wos",
        })

    @http.route("/my/workorders/<int:wo_id>/acknowledge", type="http", auth="user",
                  website=True, methods=["POST"], csrf=True)
    def portal_wo_acknowledge(self, wo_id, **kw):
        partner = request.env.user.partner_id
        wo = request.env["buruuj.workorder"].sudo().browse(wo_id)
        if wo.subcontract_id.partner_id != partner:
            return request.render("http_routing.404")
        try:
            wo.portal_acknowledge()
        except UserError as e:
            return request.render("buruuj_portal.portal_error", {
                "error": str(e),
            })
        return request.redirect(f"/my/workorders/{wo_id}")

    # ------------------------------------------------------------------
    # SUBCONTRACTOR IPCs
    # ------------------------------------------------------------------
    @http.route("/my/sub-ipcs", type="http", auth="user", website=True)
    def portal_sub_ipcs(self, **kw):
        partner = request.env.user.partner_id
        ipcs = request.env["buruuj.ipc"]._portal_get_for_partner(partner).filtered(
            lambda i: i.type == "subcontractor")
        return request.render("buruuj_portal.portal_my_sub_ipcs", {
            "ipcs": ipcs,
            "page_name": "buruuj_sub_ipcs",
        })

    @http.route("/my/sub-ipcs/<int:ipc_id>", type="http", auth="user", website=True)
    def portal_sub_ipc_detail(self, ipc_id, **kw):
        partner = request.env.user.partner_id
        ipc = request.env["buruuj.ipc"].sudo().browse(ipc_id)
        if not (ipc.type == "subcontractor" and ipc.partner_id == partner):
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_sub_ipc_detail", {
            "ipc": ipc,
            "page_name": "buruuj_sub_ipcs",
        })

    @http.route("/my/sub-ipcs/new", type="http", auth="user", website=True)
    def portal_sub_ipc_new_form(self, sub_id=None, **kw):
        partner = request.env.user.partner_id
        subs = request.env["buruuj.subcontract"]._portal_get_for_partner(
            partner).filtered(lambda s: s.state in ("signed", "in_progress"))
        return request.render("buruuj_portal.portal_sub_ipc_new", {
            "subs": subs,
            "selected_sub_id": int(sub_id) if sub_id else False,
            "page_name": "buruuj_sub_ipcs",
        })

    @http.route("/my/sub-ipcs/submit", type="http", auth="user",
                  website=True, methods=["POST"], csrf=True)
    def portal_sub_ipc_submit(self, sub_id=None, period_from=None, period_to=None,
                                claimed_amount=None, materials_on_site=None,
                                notes="", **kw):
        partner = request.env.user.partner_id
        if not sub_id:
            return request.render("buruuj_portal.portal_error", {
                "error": _("Please select a subcontract."),
            })
        sub = request.env["buruuj.subcontract"].sudo().browse(int(sub_id))
        if sub.partner_id != partner:
            return request.render("http_routing.404")
        try:
            claimed = float(claimed_amount or 0)
            mos = float(materials_on_site or 0)
        except (ValueError, TypeError):
            return request.render("buruuj_portal.portal_error", {
                "error": _("Amounts must be numeric."),
            })
        if claimed <= 0:
            return request.render("buruuj_portal.portal_error", {
                "error": _("Claimed amount must be greater than zero."),
            })
        # Determine next sequence number
        existing = request.env["buruuj.ipc"].sudo().search([
            ("subcontract_id", "=", sub.id),
            ("type", "=", "subcontractor"),
        ])
        next_seq = (max(existing.mapped("sequence_no"), default=0) or 0) + 1
        ipc_vals = {
            "type": "subcontractor",
            "sequence_no": next_seq,
            "subcontract_id": sub.id,
            "partner_id": partner.id,
            "project_id": sub.project_id.id,
            "period_from": period_from,
            "period_to": period_to,
            "materials_on_site": mos,
            "state": "draft",
        }
        ipc = request.env["buruuj.ipc"].sudo().create(ipc_vals)
        ipc.message_post(body=_(
            "Submitted via subcontractor portal by %(u)s. "
            "Subcontractor claimed amount: %(c).2f. Notes: %(n)s",
            u=request.env.user.name, c=claimed, n=notes or ""))
        return request.redirect(f"/my/sub-ipcs/{ipc.id}")

    # ------------------------------------------------------------------
    # BACKCHARGES
    # ------------------------------------------------------------------
    @http.route("/my/backcharges", type="http", auth="user", website=True)
    def portal_backcharges(self, **kw):
        partner = request.env.user.partner_id
        bcs = request.env["buruuj.backcharge"]._portal_get_for_partner(partner)
        return request.render("buruuj_portal.portal_my_backcharges", {
            "backcharges": bcs,
            "page_name": "buruuj_backcharges",
        })

    @http.route("/my/backcharges/<int:bc_id>", type="http", auth="user", website=True)
    def portal_backcharge_detail(self, bc_id, **kw):
        partner = request.env.user.partner_id
        bc = request.env["buruuj.backcharge"].sudo().browse(bc_id)
        if bc.subcontract_id.partner_id != partner:
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_backcharge_detail", {
            "bc": bc,
            "page_name": "buruuj_backcharges",
        })

    @http.route("/my/backcharges/<int:bc_id>/dispute", type="http", auth="user",
                  website=True, methods=["POST"], csrf=True)
    def portal_backcharge_dispute(self, bc_id, reason="", **kw):
        partner = request.env.user.partner_id
        bc = request.env["buruuj.backcharge"].sudo().browse(bc_id)
        if bc.subcontract_id.partner_id != partner:
            return request.render("http_routing.404")
        if not reason or not reason.strip():
            return request.render("buruuj_portal.portal_error", {
                "error": _("Please provide a dispute reason."),
            })
        try:
            bc.portal_dispute(reason)
        except UserError as e:
            return request.render("buruuj_portal.portal_error", {
                "error": str(e),
            })
        return request.redirect(f"/my/backcharges/{bc_id}")
