# -*- coding: utf-8 -*-
"""Routes the client uses to view their projects, approve IPCs, review drawings, etc."""
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError, UserError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal


class BuruujClientPortal(CustomerPortal):

    # ------------------------------------------------------------------
    # PROJECTS
    # ------------------------------------------------------------------
    @http.route("/my/projects", type="http", auth="user", website=True)
    def portal_projects(self, **kw):
        partner = request.env.user.partner_id
        projects = request.env["project.project"]._portal_get_for_partner(partner)
        return request.render("buruuj_portal.portal_my_projects", {
            "projects": projects,
            "page_name": "buruuj_projects",
        })

    @http.route("/my/projects/<int:project_id>", type="http", auth="user", website=True)
    def portal_project_detail(self, project_id, **kw):
        partner = request.env.user.partner_id
        project = request.env["project.project"].sudo().browse(project_id)
        # Access check
        if project.partner_id != partner:
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_project_detail", {
            "project": project,
            "page_name": "buruuj_projects",
        })

    # ------------------------------------------------------------------
    # CLIENT IPCs
    # ------------------------------------------------------------------
    @http.route("/my/ipcs", type="http", auth="user", website=True)
    def portal_ipcs(self, **kw):
        partner = request.env.user.partner_id
        ipcs = request.env["buruuj.ipc"]._portal_get_for_partner(partner).filtered(
            lambda i: i.type == "client")
        return request.render("buruuj_portal.portal_my_ipcs", {
            "ipcs": ipcs,
            "page_name": "buruuj_ipcs",
        })

    @http.route("/my/ipcs/<int:ipc_id>", type="http", auth="user", website=True)
    def portal_ipc_detail(self, ipc_id, **kw):
        partner = request.env.user.partner_id
        ipc = request.env["buruuj.ipc"].sudo().browse(ipc_id)
        # Access check
        if not (ipc.type == "client" and ipc.project_id.partner_id == partner):
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_ipc_detail", {
            "ipc": ipc,
            "page_name": "buruuj_ipcs",
        })

    @http.route("/my/ipcs/<int:ipc_id>/approve", type="http", auth="user",
                  website=True, methods=["POST"], csrf=True)
    def portal_ipc_approve(self, ipc_id, **kw):
        partner = request.env.user.partner_id
        ipc = request.env["buruuj.ipc"].sudo().browse(ipc_id)
        if not (ipc.type == "client" and ipc.project_id.partner_id == partner):
            return request.render("http_routing.404")
        try:
            ipc.portal_action_approve()
        except UserError as e:
            return request.render("buruuj_portal.portal_error", {
                "error": str(e),
            })
        return request.redirect(f"/my/ipcs/{ipc_id}")

    # ------------------------------------------------------------------
    # RFIs
    # ------------------------------------------------------------------
    @http.route("/my/rfis", type="http", auth="user", website=True)
    def portal_rfis(self, **kw):
        partner = request.env.user.partner_id
        rfis = request.env["buruuj.rfi"]._portal_get_for_partner(partner)
        return request.render("buruuj_portal.portal_my_rfis", {
            "rfis": rfis,
            "page_name": "buruuj_rfis",
        })

    @http.route("/my/rfis/<int:rfi_id>", type="http", auth="user", website=True)
    def portal_rfi_detail(self, rfi_id, **kw):
        partner = request.env.user.partner_id
        rfi = request.env["buruuj.rfi"].sudo().browse(rfi_id)
        if rfi.sent_to != partner:
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_rfi_detail", {
            "rfi": rfi,
            "page_name": "buruuj_rfis",
        })

    @http.route("/my/rfis/<int:rfi_id>/respond", type="http", auth="user",
                  website=True, methods=["POST"], csrf=True)
    def portal_rfi_respond(self, rfi_id, response_text="", **kw):
        partner = request.env.user.partner_id
        rfi = request.env["buruuj.rfi"].sudo().browse(rfi_id)
        if rfi.sent_to != partner:
            return request.render("http_routing.404")
        if not response_text or not response_text.strip():
            return request.render("buruuj_portal.portal_error", {
                "error": _("Response cannot be empty."),
            })
        try:
            rfi.portal_respond(response_text)
        except UserError as e:
            return request.render("buruuj_portal.portal_error", {
                "error": str(e),
            })
        return request.redirect(f"/my/rfis/{rfi_id}")

    # ------------------------------------------------------------------
    # VARIATION ORDERS
    # ------------------------------------------------------------------
    @http.route("/my/variations", type="http", auth="user", website=True)
    def portal_variations(self, **kw):
        partner = request.env.user.partner_id
        vos = request.env["buruuj.variation"]._portal_get_for_partner(partner)
        return request.render("buruuj_portal.portal_my_variations", {
            "variations": vos,
            "page_name": "buruuj_variations",
        })

    @http.route("/my/variations/<int:vo_id>", type="http", auth="user", website=True)
    def portal_variation_detail(self, vo_id, **kw):
        partner = request.env.user.partner_id
        vo = request.env["buruuj.variation"].sudo().browse(vo_id)
        if vo.project_id.partner_id != partner:
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_variation_detail", {
            "vo": vo,
            "page_name": "buruuj_variations",
        })

    @http.route("/my/variations/<int:vo_id>/decide", type="http", auth="user",
                  website=True, methods=["POST"], csrf=True)
    def portal_variation_decide(self, vo_id, decision="", notes="", **kw):
        partner = request.env.user.partner_id
        vo = request.env["buruuj.variation"].sudo().browse(vo_id)
        if vo.project_id.partner_id != partner:
            return request.render("http_routing.404")
        try:
            vo.portal_decide(decision, notes)
        except UserError as e:
            return request.render("buruuj_portal.portal_error", {
                "error": str(e),
            })
        return request.redirect(f"/my/variations/{vo_id}")

    # ------------------------------------------------------------------
    # DRAWINGS
    # ------------------------------------------------------------------
    @http.route("/my/drawings", type="http", auth="user", website=True)
    def portal_drawings(self, **kw):
        partner = request.env.user.partner_id
        drawings = request.env["buruuj.drawing"]._portal_get_for_partner(partner)
        return request.render("buruuj_portal.portal_my_drawings", {
            "drawings": drawings,
            "page_name": "buruuj_drawings",
        })

    @http.route("/my/drawings/<int:drawing_id>", type="http", auth="user", website=True)
    def portal_drawing_detail(self, drawing_id, **kw):
        partner = request.env.user.partner_id
        d = request.env["buruuj.drawing"].sudo().browse(drawing_id)
        if d.project_id.partner_id != partner:
            return request.render("http_routing.404")
        return request.render("buruuj_portal.portal_drawing_detail", {
            "drawing": d,
            "page_name": "buruuj_drawings",
        })

    @http.route("/my/drawings/<int:drawing_id>/review", type="http", auth="user",
                  website=True, methods=["POST"], csrf=True)
    def portal_drawing_review(self, drawing_id, response="", notes="", **kw):
        partner = request.env.user.partner_id
        d = request.env["buruuj.drawing"].sudo().browse(drawing_id)
        if d.project_id.partner_id != partner:
            return request.render("http_routing.404")
        try:
            d.portal_review(response, notes)
        except UserError as e:
            return request.render("buruuj_portal.portal_error", {
                "error": str(e),
            })
        return request.redirect(f"/my/drawings/{drawing_id}")
