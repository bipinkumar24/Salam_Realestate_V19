# -*- coding: utf-8 -*-
"""Scheduled AI monitoring services.

Five cron jobs run automatically:
1. Daily license & insurance expiry scan (subcontractors)
2. Daily bond / contract key date scan
3. Daily overdue RFI scan
4. Weekly portfolio risk scan (AI-powered narrative)
5. Weekly subcontractor scorecard reminder

Each job is independently toggleable via config parameters and posts
results as activities, chatter messages, or portfolio digest records.
"""
import json
import logging
import re
from datetime import date, timedelta
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


PORTFOLIO_NARRATIVE_PROMPT = """You are a senior advisor to the CEO of Buruuj Construction Co. \
You are writing the weekly executive briefing — what should the CEO worry about this week.

You will be given JSON describing every active project: budget vs actual, schedule status, \
recent NCRs, RFIs, weather lost hours, and risk register entries.

Output ONLY valid JSON in this exact schema, no preamble or markdown:

{
  "executive_summary": "3-4 sentences. Plain English. The CEO has 2 minutes. \
Lead with what is most concerning, then what is going well.",
  "top_concerns": [
    {
      "project": "Project name",
      "concern": "One specific concern, 1 sentence",
      "recommended_action": "What to do about it, 1 sentence",
      "urgency": "this_week" | "this_month" | "monitoring"
    }
  ],
  "good_news": [
    "Brief positive items worth noting, max 3"
  ],
  "questions_for_pm_review": [
    "Specific questions the CEO might ask in the next portfolio review"
  ]
}

Rules:
- Be specific. Use project names and concrete numbers from the data.
- Be conservative on tone. No alarmism.
- If everything looks healthy, say so — don't manufacture concerns.
- Maximum 5 concerns. Maximum 3 good news items. Maximum 4 questions.
"""


class BuruujAIClient(models.AbstractModel):
    """Extend the AI client with cron-callable batch operations."""
    _inherit = 'buruuj.ai.client'

    # ------------------------------------------------------------------
    # CRON 1: License & insurance expiry scan
    # ------------------------------------------------------------------
    @api.model
    def cron_license_expiry_scan(self):
        """Daily — find subcontractors with expiring credentials and alert PMs."""
        ICP = self.env['ir.config_parameter'].sudo()
        if not ICP.get_param('buruuj_ai.cron_license_scan_enabled', 'True') == 'True':
            return

        today = date.today()
        warning_window = int(
            ICP.get_param('buruuj_ai.license_warning_days', '30'))
        critical_window = 7

        partners = self.env['res.partner'].search([
            ('is_subcontractor', '=', True),
            ('active', '=', True),
        ])

        alerts_sent = 0
        for partner in partners:
            issues = []
            if partner.trade_license_expiry:
                days = (partner.trade_license_expiry - today).days
                if days <= warning_window:
                    severity = 'CRITICAL' if days <= critical_window else 'warning'
                    if days < 0:
                        issues.append(('trade_license', 'EXPIRED', days))
                    else:
                        issues.append(('trade_license', severity, days))
            if partner.insurance_expiry:
                days = (partner.insurance_expiry - today).days
                if days <= warning_window:
                    severity = 'CRITICAL' if days <= critical_window else 'warning'
                    if days < 0:
                        issues.append(('insurance', 'EXPIRED', days))
                    else:
                        issues.append(('insurance', severity, days))
            if partner.workmen_comp_expiry:
                days = (partner.workmen_comp_expiry - today).days
                if days <= warning_window:
                    severity = 'CRITICAL' if days <= critical_window else 'warning'
                    if days < 0:
                        issues.append(('workmen_comp', 'EXPIRED', days))
                    else:
                        issues.append(('workmen_comp', severity, days))

            if not issues:
                continue

            # Find related project managers (via active subcontracts)
            active_subs = self.env['buruuj.subcontract'].search([
                ('partner_id', '=', partner.id),
                ('state', 'in', ['signed', 'in_progress']),
            ])
            pms = active_subs.mapped('project_id.buruuj_pm_id') | active_subs.mapped(
                'create_uid')
            pms = pms.filtered(lambda u: u.active)

            # Compose alert message
            lines = []
            for kind, severity, days in issues:
                label = {
                    'trade_license': 'Trade License',
                    'insurance': 'Insurance',
                    'workmen_comp': "Workmen's Compensation",
                }[kind]
                if severity == 'EXPIRED':
                    lines.append(f"<li><strong style='color:#B00020'>"
                                  f"{label} EXPIRED {-days} days ago</strong></li>")
                elif severity == 'CRITICAL':
                    lines.append(f"<li><strong style='color:#B00020'>"
                                  f"{label} expires in {days} days (CRITICAL)</strong></li>")
                else:
                    lines.append(f"<li><strong style='color:#B8860B'>"
                                  f"{label} expires in {days} days</strong></li>")

            body = (
                f"<p><strong>Credential expiry alert for {partner.name}:</strong></p>"
                f"<ul>{''.join(lines)}</ul>"
                f"<p>Action required: chase the subcontractor for renewed documents. "
                f"Subcontracts cannot be approved while credentials are expired.</p>"
            )

            # Post on partner record
            partner.message_post(
                body=body,
                subject=f"[Buruuj AI] Credential expiry: {partner.name}",
            )

            # Schedule activities for active project PMs
            for pm in pms:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env['ir.model']._get(
                        'res.partner').id,
                    'res_id': partner.id,
                    'activity_type_id': self.env.ref(
                        'mail.mail_activity_data_todo').id,
                    'summary': f"Credential expiry: {partner.name}",
                    'note': body,
                    'date_deadline': today + timedelta(days=3),
                    'user_id': pm.id,
                })
                alerts_sent += 1

        _logger.info("License expiry scan: %d alerts posted", alerts_sent)
        return alerts_sent

    # ------------------------------------------------------------------
    # CRON 2: Bond / contract key date scan
    # ------------------------------------------------------------------
    @api.model
    def cron_contract_key_dates_scan(self):
        """Daily — flag bonds and insurance on contracts within 30 days."""
        ICP = self.env['ir.config_parameter'].sudo()
        if not ICP.get_param('buruuj_ai.cron_contract_scan_enabled', 'True') == 'True':
            return

        today = date.today()
        warning_window = int(
            ICP.get_param('buruuj_ai.contract_warning_days', '30'))

        contracts = self.env['buruuj.contract'].search([
            ('state', '=', 'active'),
        ])

        alerts_sent = 0
        for contract in contracts:
            issues = []
            for fname, label in [
                ('performance_bond_expiry', 'Performance Bond'),
                ('advance_bond_expiry', 'Advance Bond'),
                ('insurance_expiry', 'Insurance'),
                ('completion_date', 'Completion Date'),
                ('dlp_end_date', 'DLP End'),
            ]:
                d = contract[fname]
                if d:
                    days = (d - today).days
                    if 0 <= days <= warning_window:
                        issues.append((label, days, fname))
                    elif days < 0 and fname in (
                            'performance_bond_expiry', 'advance_bond_expiry',
                            'insurance_expiry'):
                        issues.append((label, days, fname))

            if not issues:
                continue

            lines = []
            for label, days, _fname in issues:
                if days < 0:
                    color = '#B00020'
                    text = f"{label} EXPIRED {-days} days ago"
                elif days <= 7:
                    color = '#B00020'
                    text = f"{label} expires in {days} days (URGENT)"
                else:
                    color = '#B8860B'
                    text = f"{label} expires in {days} days"
                lines.append(f"<li><strong style='color:{color}'>{text}</strong></li>")

            body = (
                f"<p><strong>Key date alert on contract {contract.name}:</strong></p>"
                f"<ul>{''.join(lines)}</ul>"
            )

            contract.message_post(
                body=body,
                subject=f"[Buruuj AI] Key dates: {contract.name}",
            )

            # Activity for the project PM
            project = contract.project_id
            pm = project.buruuj_pm_id if project else False
            if pm:
                self.env['mail.activity'].sudo().create({
                    'res_model_id': self.env['ir.model']._get(
                        'buruuj.contract').id,
                    'res_id': contract.id,
                    'activity_type_id': self.env.ref(
                        'mail.mail_activity_data_todo').id,
                    'summary': f"Key date: {contract.name}",
                    'note': body,
                    'date_deadline': today + timedelta(days=2),
                    'user_id': pm.id,
                })
                alerts_sent += 1

        _logger.info("Contract key dates scan: %d alerts posted", alerts_sent)
        return alerts_sent

    # ------------------------------------------------------------------
    # CRON 3: Overdue RFI scan
    # ------------------------------------------------------------------
    @api.model
    def cron_overdue_rfi_scan(self):
        """Daily — flag RFIs past their response_due date."""
        ICP = self.env['ir.config_parameter'].sudo()
        if not ICP.get_param('buruuj_ai.cron_rfi_scan_enabled', 'True') == 'True':
            return

        today = date.today()
        rfis = self.env['buruuj.rfi'].search([
            ('state', 'in', ['sent']),
            ('response_due', '<', today),
        ])

        alerts_sent = 0
        for rfi in rfis:
            days_overdue = (today - rfi.response_due).days
            body = (
                f"<p><strong>RFI {rfi.name} is {days_overdue} day(s) overdue.</strong></p>"
                f"<p>Title: {rfi.title}<br/>"
                f"Sent to: {rfi.sent_to.name if rfi.sent_to else 'Unspecified'}<br/>"
                f"Due: {rfi.response_due}</p>"
                f"<p>Action: chase the consultant for a response. "
                f"Consider escalating to the project manager.</p>"
            )

            rfi.message_post(
                body=body,
                subject=f"[Buruuj AI] RFI overdue: {rfi.name}",
            )

            if rfi.raised_by:
                # Avoid duplicate activities — check if one exists
                existing = self.env['mail.activity'].search([
                    ('res_model', '=', 'buruuj.rfi'),
                    ('res_id', '=', rfi.id),
                    ('user_id', '=', rfi.raised_by.id),
                    ('summary', 'like', 'RFI overdue'),
                ], limit=1)
                if not existing:
                    self.env['mail.activity'].sudo().create({
                        'res_model_id': self.env['ir.model']._get('buruuj.rfi').id,
                        'res_id': rfi.id,
                        'activity_type_id': self.env.ref(
                            'mail.mail_activity_data_todo').id,
                        'summary': f"RFI overdue {days_overdue}d: {rfi.title[:60]}",
                        'note': body,
                        'date_deadline': today,
                        'user_id': rfi.raised_by.id,
                    })
                    alerts_sent += 1

        _logger.info("Overdue RFI scan: %d alerts posted", alerts_sent)
        return alerts_sent

    # ------------------------------------------------------------------
    # CRON 4: Weekly portfolio risk scan (AI-powered)
    # ------------------------------------------------------------------
    @api.model
    def cron_portfolio_risk_scan(self):
        """Weekly — AI generates an executive narrative across the portfolio."""
        ICP = self.env['ir.config_parameter'].sudo()
        if not ICP.get_param('buruuj_ai.cron_portfolio_scan_enabled', 'True') == 'True':
            return
        if not self.is_enabled():
            _logger.info("Portfolio scan skipped — AI not configured")
            return

        # Gather portfolio data
        today = date.today()
        week_ago = today - timedelta(days=7)
        projects = self.env['project.project'].search([
            ('buruuj_project_code', '!=', False),
            ('active', '=', True),
        ])

        if not projects:
            _logger.info("Portfolio scan: no active projects")
            return

        portfolio_data = []
        for project in projects:
            # Recent DPRs
            recent_dprs = self.env['buruuj.dpr'].search([
                ('project_id', '=', project.id),
                ('date', '>=', week_ago),
            ])
            weather_loss_hours = sum(recent_dprs.mapped('rain_hours') or [0.0])

            # Open NCRs
            ncrs_open = self.env['buruuj.ncr'].search_count([
                ('project_id', '=', project.id),
                ('state', 'in', ['issued', 'action_in_progress']),
            ])
            ncrs_critical = self.env['buruuj.ncr'].search_count([
                ('project_id', '=', project.id),
                ('state', 'in', ['issued', 'action_in_progress']),
                ('severity', '=', 'critical'),
            ])

            # Overdue RFIs
            rfis_overdue = self.env['buruuj.rfi'].search_count([
                ('project_id', '=', project.id),
                ('state', '=', 'sent'),
                ('response_due', '<', today),
            ])

            # Open risks
            high_risks = self.env['buruuj.risk'].search([
                ('project_id', '=', project.id),
                ('state', '=', 'open'),
                ('severity', '>=', 12),
            ])

            portfolio_data.append({
                'project_id': project.id,
                'name': project.name,
                'code': project.buruuj_project_code,
                'health': project.buruuj_health,
                'physical_progress_pct': round(project.buruuj_physical_progress or 0, 1),
                'financial_progress_pct': round(project.buruuj_financial_progress or 0, 1),
                'planned_end': str(project.buruuj_planned_end or ''),
                'days_until_planned_end': (
                    (project.buruuj_planned_end - today).days
                    if project.buruuj_planned_end else None),
                'baseline_budget': project.buruuj_baseline_budget,
                'revised_budget': project.buruuj_revised_budget,
                'actual_cost': project.buruuj_actual_cost,
                'recent_dpr_count': len(recent_dprs),
                'weather_loss_hours_week': round(weather_loss_hours, 1),
                'ncrs_open': ncrs_open,
                'ncrs_critical_open': ncrs_critical,
                'rfis_overdue': rfis_overdue,
                'high_risks': [{
                    'title': r.name,
                    'category': r.category,
                    'severity': r.severity,
                    'mitigation': (r.mitigation or '')[:200],
                } for r in high_risks],
            })

        # Build the AI request
        user_msg = (
            f"Portfolio snapshot — week ending {today}.\n"
            f"Buruuj Construction has {len(portfolio_data)} active projects.\n\n"
            f"Project data:\n{json.dumps(portfolio_data, indent=2)}"
        )

        try:
            result = self.complete(
                system=PORTFOLIO_NARRATIVE_PROMPT,
                messages=[{"role": "user", "content": user_msg}],
                max_tokens=2048,
                task_type='generic',
            )
        except Exception as e:
            _logger.exception("Portfolio scan AI call failed: %s", e)
            return

        text = result['text'].strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```\s*$', '', text)

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            _logger.error("Portfolio narrative not valid JSON: %s", text[:500])
            return

        # Create a digest record
        digest = self.env['buruuj.portfolio.digest'].create({
            'date': today,
            'executive_summary': parsed.get('executive_summary', ''),
            'top_concerns_json': json.dumps(parsed.get('top_concerns', [])),
            'good_news_json': json.dumps(parsed.get('good_news', [])),
            'questions_json': json.dumps(parsed.get('questions_for_pm_review', [])),
            'project_count': len(portfolio_data),
            'ai_task_id': result['task_id'],
        })

        # Email/notify Directors
        directors = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('buruuj_base.group_buruuj_director').id),
            ('active', '=', True),
        ])
        for director in directors:
            digest.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f"Weekly Portfolio Briefing — {today}",
                note=f"<p>Weekly executive briefing is ready.</p>"
                     f"<p>{parsed.get('executive_summary', '')}</p>",
                user_id=director.id,
                date_deadline=today + timedelta(days=2),
            )

        _logger.info("Portfolio risk scan complete: digest %s", digest.name)
        return digest.id

    # ------------------------------------------------------------------
    # CRON 5: Weekly subcontractor scorecard reminder
    # ------------------------------------------------------------------
    @api.model
    def cron_scorecard_reminder(self):
        """Weekly — remind PMs to score active subcontracts they haven't yet."""
        ICP = self.env['ir.config_parameter'].sudo()
        if not ICP.get_param('buruuj_ai.cron_scorecard_reminder_enabled', 'True') == 'True':
            return

        today = date.today()
        # Define current quarter
        quarter = (today.month - 1) // 3 + 1
        year = today.year
        quarter_label = f"Q{quarter} {year}"
        quarter_start = date(year, (quarter - 1) * 3 + 1, 1)

        active_subs = self.env['buruuj.subcontract'].search([
            ('state', 'in', ['signed', 'in_progress']),
        ])

        reminders_sent = 0
        for sub in active_subs:
            # Has there been a scorecard for this partner+project this quarter?
            existing = self.env['buruuj.scorecard'].search_count([
                ('partner_id', '=', sub.partner_id.id),
                ('project_id', '=', sub.project_id.id),
                ('date', '>=', quarter_start),
            ])
            if existing:
                continue

            project = sub.project_id
            pm = project.buruuj_pm_id if project else False
            if not pm:
                continue

            # Avoid duplicates
            existing_act = self.env['mail.activity'].search([
                ('res_model', '=', 'buruuj.subcontract'),
                ('res_id', '=', sub.id),
                ('user_id', '=', pm.id),
                ('summary', 'like', 'Scorecard reminder'),
            ], limit=1)
            if existing_act:
                continue

            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env['ir.model']._get(
                    'buruuj.subcontract').id,
                'res_id': sub.id,
                'activity_type_id': self.env.ref(
                    'mail.mail_activity_data_todo').id,
                'summary': f"Scorecard reminder: {sub.partner_id.name} ({quarter_label})",
                'note': (
                    f"<p>Quarterly scorecard not yet completed for "
                    f"<strong>{sub.partner_id.name}</strong> on "
                    f"<strong>{project.name}</strong> for {quarter_label}.</p>"
                    f"<p>Please score the subcontractor on Quality, Schedule, Safety, "
                    f"and Payment Compliance.</p>"
                ),
                'date_deadline': today + timedelta(days=14),
                'user_id': pm.id,
            })
            reminders_sent += 1

        _logger.info("Scorecard reminders: %d sent", reminders_sent)
        return reminders_sent
