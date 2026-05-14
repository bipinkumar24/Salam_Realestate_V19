# -*- coding: utf-8 -*-
# from odoo import http


# class OwnershipApproval2(http.Controller):
#     @http.route('/ownership_approval2/ownership_approval2', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ownership_approval2/ownership_approval2/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ownership_approval2.listing', {
#             'root': '/ownership_approval2/ownership_approval2',
#             'objects': http.request.env['ownership_approval2.ownership_approval2'].search([]),
#         })

#     @http.route('/ownership_approval2/ownership_approval2/objects/<model("ownership_approval2.ownership_approval2"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ownership_approval2.object', {
#             'object': obj
#         })
