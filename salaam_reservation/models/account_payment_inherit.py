# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountPaymentReservation(models.Model):
    """
    Extends account.payment to link it to a salaam.reservation.
    Deposit payments are posted by directly writing the move state in SQL,
    completely bypassing both our action_post override AND the
    real_estate_commission override — breaking the infinite recursion loop.
    """
    _inherit = 'account.payment'

    reservation_id = fields.Many2one(
        'salaam.reservation',
        string='Reservation',
        index=True,
        help='The off-plan reservation this payment is a deposit for',
    )
    is_reservation_deposit = fields.Boolean(
        string='Reservation Deposit',
        default=False,
        help='Mark this payment as a reservation deposit',
    )

    def action_post(self):
        """
        Deposit payments: post the underlying journal entry directly via
        account.move's _post() internal method, which does NOT call
        payment.action_post() back — breaking the recursion.

        Regular payments: normal flow (commission module runs).
        """
        deposit_payments = self.filtered(
            lambda p: p.is_reservation_deposit
        )
        regular_payments = self - deposit_payments

        # Regular payments — full flow including commission
        if regular_payments:
            super(AccountPaymentReservation, regular_payments).action_post()

        # Deposit payments — post journal entry directly, NO recursion
        for payment in deposit_payments:
            if payment.state != 'draft':
                continue
            move = payment.move_id
            if move and move.state == 'draft':
                # Call account.move._post() directly — internal method that
                # does NOT call payment.action_post() back
                move._post(soft=False)
