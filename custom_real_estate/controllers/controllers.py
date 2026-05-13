# -*- coding: utf-8 -*-
# from odoo import http


# class CustomRealEstate(http.Controller):
#     @http.route('/custom_real_estate/custom_real_estate', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_real_estate/custom_real_estate/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_real_estate.listing', {
#             'root': '/custom_real_estate/custom_real_estate',
#             'objects': http.request.env['custom_real_estate.custom_real_estate'].search([]),
#         })

#     @http.route('/custom_real_estate/custom_real_estate/objects/<model("custom_real_estate.custom_real_estate"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_real_estate.object', {
#             'object': obj
#         })
