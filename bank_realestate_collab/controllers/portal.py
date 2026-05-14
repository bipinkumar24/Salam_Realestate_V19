# -*- coding: utf-8 -*-
import json
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class BREPortal(CustomerPortal):
    """Portal controller for BRE Customer Applications."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        if 'bre_application_count' in counters:
            values['bre_application_count'] = request.env[
                'bre.customer.application'].sudo().search_count(
                [('partner_id', '=', partner.id)])
        if 'bre_property_count' in counters:
            values['bre_property_count'] = request.env[
                'property.details'].sudo().search_count(
                [('stage', '=', 'available')])
        return values

    # ── helpers ──────────────────────────────────────────────────────────────
    def _app_to_dict(self, app):
        bank_status_labels = {
            'not_submitted': 'Not Submitted',
            'pending':       'Pending Review',
            'under_review':  'Under Review',
            'approved':      'Approved',
            'rejected':      'Rejected',
            'on_hold':       'On Hold',
        }
        financing_labels = {
            'murabaha':              'Murabaha',
            'ijara':                 'Ijara',
            'diminishing_musharaka': 'Diminishing Musharaka',
            'conventional':          'Conventional Mortgage',
            'cash':                  'Cash Purchase',
        }
        docs = []
        for doc in app.document_ids:
            docs.append({
                'name':   doc.name or '',
                'type':   doc.document_category or '',
                'status': doc.verification_status or 'pending',
            })
        return {
            'id':               app.id,
            'name':             app.name or '',
            'url':              f'/my/applications/{app.id}',
            'customer_name':    app.customer_name or '',
            'application_date': app.application_date.strftime('%d %b %Y') if app.application_date else '',
            'bank_status':      app.bank_status or 'not_submitted',
            'bank_status_label': bank_status_labels.get(app.bank_status, ''),
            'stage':            app.stage_id.name if app.stage_id else '',
            'prioritization_number':      app.prioritization_number or '',
            'prioritization_file_number': app.prioritization_file_number or '',
            # Property
            'property_name':    app.property_id.name if app.property_id else '',
            'property_type':    app.property_type_mirror or '',
            'property_city':    app.property_city or '',
            'property_price':   app.property_price or 0,
            'property_area':    app.property_total_area or 0,
            'property_project': app.property_project.name if app.property_project else '',
            'property_subproject': app.property_subproject.name if app.property_subproject else '',
            'property_zone':    app.property_zone.name if app.property_zone else '',
            'property_lot':     app.property_lot.name if app.property_lot else '',
            'property_block':   app.property_block.name if app.property_block else '',
            'property_tf_no':   app.property_tf_no or '',
            'property_id_no':   app.property_sequence_no or '',
            # Financing
            'financing_type':   financing_labels.get(app.financing_type, app.financing_type or ''),
            'financing_amount': app.financing_amount or 0,
            'down_payment':     app.down_payment or 0,
            'tenure_months':    app.tenure_months or 0,
            'currency_symbol':  app.currency_id.symbol if app.currency_id else '',
            # Progress / bank decision
            'progress':         app.progress or 0,
            'agent':            app.agent_id.name if app.agent_id else '',
            'bank_officer':     app.bank_officer_id.name if app.bank_officer_id else '',
            'submission_date':  app.submission_date.strftime('%d %b %Y') if app.submission_date else '',
            'decision_date':    app.decision_date.strftime('%d %b %Y') if app.decision_date else '',
            'approved_amount':  app.approved_amount or 0,
            'approved_tenure':  app.approved_tenure or 0,
            'approved_rate':    app.approved_rate or 0,
            'conditions':       app.conditions or '',
            'rejection_reason': app.rejection_reason or '',
            'documents':        docs,
        }

    # ── list page ─────────────────────────────────────────────────────────────
    @http.route(['/my/applications', '/my/applications/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_applications(self, page=1, **kw):
        partner = request.env.user.partner_id
        domain = [('partner_id', '=', partner.id)]
        App = request.env['bre.customer.application'].sudo()
        total = App.search_count(domain)
        pager = portal_pager(url='/my/applications', total=total, page=page, step=20)
        applications = App.search(domain, order='create_date desc',
                                  limit=20, offset=pager['offset'])
        records_json = json.dumps([self._app_to_dict(a) for a in applications])
        return request.render('bank_realestate_collab.portal_applications_list', {
            'applications':  applications,
            'records_json':  records_json,
            'pager':         pager,
            'page_name':     'applications',
            'default_url':   '/my/applications',
        })

    # ── detail page ───────────────────────────────────────────────────────────
    @http.route('/my/applications/<int:app_id>', type='http', auth='user', website=True)
    def portal_application_detail(self, app_id, **kw):
        partner = request.env.user.partner_id
        app = request.env['bre.customer.application'].sudo().search([
            ('id', '=', app_id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        if not app:
            return request.redirect('/my/applications')
        app_json = json.dumps(self._app_to_dict(app))
        return request.render('bank_realestate_collab.portal_application_detail', {
            'application': app,
            'app_json':    app_json,
            'page_name':   'applications',
        })


class BREPropertyPortal(http.Controller):
    """Public/portal property listing and selection."""

    # ── Available properties listing ──────────────────────────────────────────
    @http.route(['/properties', '/properties/page/<int:page>'],
                type='http', auth='public', website=True)
    def properties_list(self, page=1, ptype=None, **kw):
        domain = [('stage', '=', 'available')]
        if ptype:
            domain.append(('type', '=', ptype))

        Prop = request.env['property.details'].sudo()
        total = Prop.search_count(domain)
        pager = portal_pager(url='/properties', total=total, page=page, step=12)
        properties = Prop.search(domain, order='id desc',
                                 limit=12, offset=pager['offset'])

        # Check if current user has a prio# (via any prioritization record)
        has_prio = False
        prio_number = ''
        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            partner = request.env.user.partner_id
            app = request.env['bre.customer.application'].sudo().search(
                [('partner_id', '=', partner.id),
                 ('prioritization_number', '!=', False)],
                limit=1, order='id desc'
            )
            if app:
                has_prio = True
                prio_number = app.prioritization_number

        return request.render('bank_realestate_collab.portal_properties_list', {
            'properties':   properties,
            'pager':        pager,
            'ptype':        ptype or '',
            'has_prio':     has_prio,
            'prio_number':  prio_number,
            'page_name':    'properties',
        })

    # ── Single property detail ────────────────────────────────────────────────
    @http.route('/properties/<int:prop_id>',
                type='http', auth='public', website=True)
    def property_detail(self, prop_id, **kw):
        prop = request.env['property.details'].sudo().browse(prop_id)
        if not prop.exists() or prop.stage != 'available':
            return request.redirect('/properties')

        has_prio = False
        prio_number = ''
        existing_app = None
        if request.env.user and request.env.user.id != request.env.ref('base.public_user').id:
            partner = request.env.user.partner_id
            app = request.env['bre.customer.application'].sudo().search(
                [('partner_id', '=', partner.id),
                 ('prioritization_number', '!=', False)],
                limit=1, order='id desc'
            )
            if app:
                has_prio = True
                prio_number = app.prioritization_number
            # Check if already applied for this property
            existing_app = request.env['bre.customer.application'].sudo().search(
                [('partner_id', '=', partner.id),
                 ('property_id', '=', prop_id)],
                limit=1
            )

        return request.render('bank_realestate_collab.portal_property_detail', {
            'prop':         prop,
            'has_prio':     has_prio,
            'prio_number':  prio_number,
            'existing_app': existing_app,
            'page_name':    'properties',
        })

    # ── Select property — create application ──────────────────────────────────
    @http.route('/properties/<int:prop_id>/select',
                type='http', auth='user', website=True, methods=['POST'])
    def property_select(self, prop_id, **kw):
        partner = request.env.user.partner_id

        # Must have a prio#
        app_with_prio = request.env['bre.customer.application'].sudo().search(
            [('partner_id', '=', partner.id),
             ('prioritization_number', '!=', False)],
            limit=1, order='id desc'
        )
        if not app_with_prio:
            return request.redirect('/properties?error=no_prio')

        prop = request.env['property.details'].sudo().browse(prop_id)
        if not prop.exists() or prop.stage != 'available':
            return request.redirect('/properties?error=unavailable')

        # Check for existing application on this property
        existing = request.env['bre.customer.application'].sudo().search(
            [('partner_id', '=', partner.id),
             ('property_id', '=', prop_id)],
            limit=1
        )
        if existing:
            return request.redirect('/my/applications/%d' % existing.id)

        # Create new application pre-filled with property
        stage = request.env['bre.application.stage'].sudo().search(
            [], order='sequence asc', limit=1)

        new_app = request.env['bre.customer.application'].sudo().create({
            'partner_id':          partner.id,
            'property_id':         prop_id,
            'stage_id':            stage.id if stage else False,
            'prioritization_id':   app_with_prio.prioritization_id.id,
            'agent_id':            request.env.user.id,
            'financing_type':      'murabaha',
            'financing_amount':    prop.price or 0,
            'date_of_birth':       partner.birthday or '1990-01-01',
            'gender':              'male',
            'nationality_id':      partner.country_id.id or
                                   request.env.ref('base.dj', raise_if_not_found=False) and
                                   request.env.ref('base.dj').id or False,
            'email':               partner.email or '',
            'mobile':              partner.mobile or partner.phone or '',
        })

        # Set property to booked immediately
        if prop.stage == 'available':
            prop.sudo().write({'stage': 'reserved'})
            new_app.message_post(
                body='Property <b>%s</b> set to <b>Reserved</b> upon portal property selection.'
                     % prop.name,
                subtype_xmlid='mail.mt_note',
            )

        return request.redirect('/my/applications/%d' % new_app.id)


class BREApplicationCreate(http.Controller):
    """Portal: create a new financing application."""

    def _get_user_prioritization(self):
        """Return (lead, prio) for the current portal user, or (None, None)."""
        partner = request.env.user.partner_id
        # Find CRM lead linked to this partner
        lead = request.env['crm.lead'].sudo().search(
            [('partner_id', '=', partner.id)],
            order='create_date desc', limit=1
        )
        if not lead:
            return None, None
        prio = request.env['unit.prioritization'].sudo().search(
            [('opportunity_id', '=', lead.id)], limit=1
        )
        return lead, prio

    @http.route('/my/applications/new', type='http', auth='user', website=True)
    def new_application_form(self, **kw):
        """Show the create-application form."""
        lead, prio = self._get_user_prioritization()
        partner = request.env.user.partner_id

        if not prio:
            return request.render(
                'bank_realestate_collab.portal_application_no_prio', {})

        # Available properties for selection
        properties = request.env['property.details'].sudo().search(
            [('stage', '=', 'available')], order='id desc')

        # Countries for nationality dropdown
        countries = request.env['res.country'].sudo().search([], order='name')

        error = kw.get('error', '')
        return request.render('bank_realestate_collab.portal_application_new', {
            'partner':      partner,
            'lead':         lead,
            'prio':         prio,
            'properties':   properties,
            'countries':    countries,
            'error':        error,
            'values':       kw,
        })

    @http.route('/my/applications/new/submit', type='http',
                auth='user', website=True, methods=['POST'])
    def new_application_submit(self, **kw):
        """Process the create-application form submission."""
        partner = request.env.user.partner_id
        lead, prio = self._get_user_prioritization()

        if not prio:
            return request.redirect('/my/applications/new')

        # ── Validate required fields ──────────────────────────────────────
        errors = []
        required = {
            'date_of_birth':    'Date of Birth',
            'gender':           'Gender',
            'nationality_id':   'Nationality',
            'email':            'Email',
            'mobile':           'Mobile',
            'id_number':        'ID Number',
            'id_type':          'ID Type',
            'employment_status':'Employment Status',
            'employer_name':    'Employer / Business Name',
            'monthly_income':   'Monthly Income',
            'financing_type':   'Payment / Financing Type',
            'property_id':      'Selected Property',
        }
        # financing_amount only required when NOT cash
        is_cash = kw.get('financing_type') == 'cash'
        if not is_cash:
            required['financing_amount'] = 'Financing Amount'
        for field, label in required.items():
            if not kw.get(field, '').strip():
                errors.append(f'{label} is required.')

        if errors:
            countries = request.env['res.country'].sudo().search([], order='name')
            properties = request.env['property.details'].sudo().search(
                [('stage', '=', 'available')], order='id desc')
            return request.render('bank_realestate_collab.portal_application_new', {
                'partner':    partner,
                'lead':       lead,
                'prio':       prio,
                'properties': properties,
                'countries':  countries,
                'errors':     errors,
                'values':     kw,
            })

        # ── Get first available stage ─────────────────────────────────────
        stage = request.env['bre.application.stage'].sudo().search(
            [], order='sequence asc', limit=1)

        # ── Build create vals ─────────────────────────────────────────────
        nationality = request.env['res.country'].sudo().browse(
            int(kw['nationality_id']))

        try:
            monthly_income = float(kw['monthly_income'].replace(',', ''))
        except Exception:
            monthly_income = 0.0

        try:
            monthly_obligations = float(kw.get('monthly_obligations', '0').replace(',', '') or '0')
        except Exception:
            monthly_obligations = 0.0

        # Cash purchase: financing_amount = 0, down_payment = cash amount entered
        is_cash = kw.get('financing_type') == 'cash'

        try:
            financing_amount = 0.0 if is_cash else float((kw.get('financing_amount') or '0').replace(',', ''))
        except Exception:
            financing_amount = 0.0

        try:
            if is_cash:
                down_payment = float((kw.get('cash_amount_display') or '0').replace(',', ''))
            else:
                down_payment = float((kw.get('down_payment') or '0').replace(',', ''))
        except Exception:
            down_payment = 0.0

        try:
            tenure_months = 0 if is_cash else int(kw.get('tenure_months', '240') or '240')
        except Exception:
            tenure_months = 0 if is_cash else 240

        vals = {
            'partner_id':          partner.id,
            'agent_id':            request.env.user.id,
            'stage_id':            stage.id if stage else False,
            'crm_lead_id':         lead.id if lead else False,
            'prioritization_id':   prio.id,
            # Personal
            'date_of_birth':       kw['date_of_birth'],
            'gender':              kw['gender'],
            'nationality_id':      nationality.id,
            'email':               kw['email'],
            'mobile':              kw['mobile'],
            'phone':               kw.get('phone', ''),
            'id_number':           kw['id_number'],
            'id_type':             kw['id_type'],
            'employment_status':   kw['employment_status'],
            'employer_name':       kw.get('employer_name', ''),
            'monthly_income':      monthly_income,
            'monthly_obligations': monthly_obligations,
            # Property & Financing
            'property_id':         int(kw['property_id']),
            'financing_type':      kw['financing_type'],
            'financing_amount':    financing_amount,
            'down_payment':        down_payment,
            'tenure_months':       tenure_months,
        }

        new_app = request.env['bre.customer.application'].sudo().create(vals)

        # Set property stage to 'booked' immediately when application is created from portal
        if new_app.property_id and new_app.property_id.stage == 'available':
            new_app.property_id.sudo().write({'stage': 'reserved_offplan'})
            new_app.message_post(
                body='Property <b>%s</b> set to <b>Reserved</b> upon portal application submission.'
                     % new_app.property_id.name,
                subtype_xmlid='mail.mt_note',
            )

        return request.redirect('/my/applications/%d' % new_app.id)
