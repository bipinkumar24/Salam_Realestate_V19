# -*- coding: utf-8 -*-
"""Weekly portfolio digest — record of each AI-generated executive briefing."""
import json
from odoo import models, fields, api


class BuruujPortfolioDigest(models.Model):
    _name = 'buruuj.portfolio.digest'
    _description = 'Weekly Portfolio Digest'
    _inherit = ['mail.thread']
    _order = 'date desc'

    name = fields.Char(compute='_compute_name', store=True)
    date = fields.Date(default=fields.Date.context_today, required=True)
    project_count = fields.Integer(string='Active Projects')

    executive_summary = fields.Html(string='Executive Summary')

    # Stored as JSON; parsed for display
    top_concerns_json = fields.Text()
    good_news_json = fields.Text()
    questions_json = fields.Text()

    # Computed display fields
    top_concerns_html = fields.Html(
        compute='_compute_html_views', store=False)
    good_news_html = fields.Html(
        compute='_compute_html_views', store=False)
    questions_html = fields.Html(
        compute='_compute_html_views', store=False)

    ai_task_id = fields.Many2one('buruuj.ai.task', readonly=True)
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company)

    @api.depends('date', 'project_count')
    def _compute_name(self):
        for rec in self:
            rec.name = f"Portfolio Digest — {rec.date or 'New'}"

    @api.depends('top_concerns_json', 'good_news_json', 'questions_json')
    def _compute_html_views(self):
        for rec in self:
            # Top concerns
            try:
                concerns = json.loads(rec.top_concerns_json or '[]')
                if concerns:
                    rows = []
                    for c in concerns:
                        urgency = c.get('urgency', 'monitoring')
                        color = {
                            'this_week': '#B00020',
                            'this_month': '#B8860B',
                            'monitoring': '#1B7F3A',
                        }.get(urgency, '#555555')
                        rows.append(
                            f"<div style='border-left:4px solid {color};"
                            f"padding:8px 12px;margin:8px 0;background:#F4F7FA;'>"
                            f"<strong style='color:#0B2545;'>{c.get('project', '')}</strong>"
                            f" <span style='color:{color};font-size:0.9em;'>"
                            f"({urgency.replace('_', ' ')})</span><br/>"
                            f"<span>{c.get('concern', '')}</span><br/>"
                            f"<em style='color:#555;'>→ {c.get('recommended_action', '')}</em>"
                            f"</div>")
                    rec.top_concerns_html = ''.join(rows)
                else:
                    rec.top_concerns_html = "<p><em>No concerns flagged this week.</em></p>"
            except (json.JSONDecodeError, TypeError):
                rec.top_concerns_html = ''

            # Good news
            try:
                items = json.loads(rec.good_news_json or '[]')
                if items:
                    rec.good_news_html = (
                        '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>')
                else:
                    rec.good_news_html = ''
            except (json.JSONDecodeError, TypeError):
                rec.good_news_html = ''

            # Questions
            try:
                qs = json.loads(rec.questions_json or '[]')
                if qs:
                    rec.questions_html = (
                        '<ul>' + ''.join(f'<li>{q}</li>' for q in qs) + '</ul>')
                else:
                    rec.questions_html = ''
            except (json.JSONDecodeError, TypeError):
                rec.questions_html = ''
