# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class CashPurchasePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'cash_plan_count' in counters:
            partner = request.env.user.partner_id
            values['cash_plan_count'] = request.env['cash.payment.plan'].search_count(
                [('partner_id', 'child_of', [partner.commercial_partner_id.id])]
            )
        return values

    @http.route('/my/payment-plans', type='http', auth='user', website=True)
    def portal_cash_plans(self, **kwargs):
        partner = request.env.user.partner_id
        plans = request.env['cash.payment.plan'].search(
            [('partner_id', 'child_of', [partner.commercial_partner_id.id])],
            order='create_date desc',
        )
        return request.render('cash_purchase.portal_my_payment_plans', {
            'plans': plans,
            'page_name': 'payment_plans',
        })

    @http.route('/my/payment-plans/<int:plan_id>', type='http', auth='user', website=True)
    def portal_cash_plan_detail(self, plan_id, **kwargs):
        partner  = request.env.user.partner_id
        plan     = request.env['cash.payment.plan'].search([
            ('id', '=', plan_id),
            ('partner_id', 'child_of', [partner.commercial_partner_id.id]),
        ], limit=1)
        if not plan:
            return request.redirect('/my/payment-plans')
        return request.render('cash_purchase.portal_cash_payment_schedule', {
            'plan':      plan,
            'page_name': 'payment_plans',
        })
