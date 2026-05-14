# -*- coding: utf-8 -*-
import base64
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError


FAKE_AI_RESULT = {
    'project_summary': 'Single-storey office, ~120 m².',
    'scale_detected': '1:100',
    'items': [
        {'category': 'civil', 'description': 'Block walls 200mm',
         'uom': 'm2', 'quantity': 80, 'unit_price_estimate': 35,
         'confidence': 0.9, 'source_reference': 'A-101'},
        {'category': 'finishes', 'description': 'Floor tiles 600x600',
         'uom': 'm2', 'quantity': 110, 'unit_price_estimate': 28,
         'confidence': 0.7, 'source_reference': 'A-102'},
        {'category': 'electrical', 'description': 'Power & lighting (LS)',
         'uom': 'lot', 'quantity': 1, 'unit_price_estimate': 4500,
         'confidence': 0.5, 'source_reference': 'E-001'},
    ],
    'warnings': ['Scale on sheet A-103 not legible.'],
    '_meta': {'provider': 'anthropic', 'model': 'claude-sonnet-4-5',
              'pages': 3, 'raw_response': '{...}'},
}


@tagged('post_install', '-at_install')
class TestBoqProject(TransactionCase):

    def setUp(self):
        super().setUp()
        self.partner = self.env['res.partner'].create({'name': 'Acme Ltd'})
        # tiny PNG (1x1 transparent) so the file-type check passes
        self.png_b64 = base64.b64encode(
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
            b'\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89'
            b'\x00\x00\x00\rIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )

    def _make_boq(self):
        return self.env['ai.boq.project'].create({
            'name': 'New',
            'partner_id': self.partner.id,
            'design_file': self.png_b64,
            'design_filename': 'test.png',
        })

    def test_create_assigns_sequence(self):
        boq = self._make_boq()
        self.assertNotEqual(boq.name, 'New')
        self.assertTrue(boq.name.startswith('BOQ/'))

    def test_analyze_requires_file(self):
        boq = self.env['ai.boq.project'].create({'name': 'New'})
        with self.assertRaises(UserError):
            boq.action_analyze()

    def test_analyze_populates_lines(self):
        boq = self._make_boq()
        with patch.object(self.env.registry['ai.boq.service'], 'analyze_design',
                          return_value=FAKE_AI_RESULT):
            boq.action_analyze()
        self.assertEqual(boq.state, 'reviewed')
        self.assertEqual(len(boq.line_ids), 3)
        self.assertEqual(boq.ai_model_used, 'claude-sonnet-4-5')
        self.assertGreater(boq.total_amount, 0)
        # confidence band check
        low = boq.line_ids.filtered(lambda l: l.confidence_band == 'low')
        self.assertTrue(low, "expected at least one low-confidence line")

    def test_approve_requires_reviewed(self):
        boq = self._make_boq()
        with self.assertRaises(UserError):
            boq.action_approve()

    def test_full_workflow(self):
        boq = self._make_boq()
        with patch.object(self.env.registry['ai.boq.service'], 'analyze_design',
                          return_value=FAKE_AI_RESULT):
            boq.action_analyze()
        boq.action_approve()
        self.assertEqual(boq.state, 'approved')

    def test_template_lines_added(self):
        tmpl = self.env['ai.boq.template'].create({
            'name': 'Test Template',
            'line_ids': [(0, 0, {
                'category': 'civil',
                'description': 'Test civil item',
                'default_quantity': 10,
                'default_unit_price': 50,
            })],
        })
        boq = self._make_boq()
        boq.template_id = tmpl
        boq._onchange_template_id()
        self.assertTrue(any('Test civil item' in l.description for l in boq.line_ids))

    def test_pricelist_check_with_linked_product(self):
        """Lines linked to a product should be re-priced from the pricelist."""
        product = self.env['product.product'].create({
            'name': 'Concrete C30 m3',
            'type': 'service',
            'list_price': 150.0,
        })
        pricelist = self.env['product.pricelist'].create({'name': 'Test PL'})

        boq = self._make_boq()
        boq.pricelist_id = pricelist
        boq.write({
            'line_ids': [(0, 0, {
                'category': 'structural',
                'description': 'Concrete',
                'product_id': product.id,
                'quantity': 10,
                'unit_price': 99.0,         # AI estimate, will be overridden
                'confidence_score': 0.6,
            })],
        })
        boq.action_pricelist_check()
        self.assertEqual(boq.price_check_state, 'matched')
        self.assertEqual(boq.line_ids[0].unit_price, 150.0)

    def test_pricelist_check_fuzzy_match(self):
        """A line with no product but a clear description should fuzzy-match."""
        self.env['product.product'].create({
            'name': 'Reinforcement Steel Y12 Bars',
            'type': 'service',
            'list_price': 1.25,
            'sale_ok': True,
        })
        pricelist = self.env['product.pricelist'].create({'name': 'Test PL 2'})

        boq = self._make_boq()
        boq.pricelist_id = pricelist
        boq.write({
            'line_ids': [(0, 0, {
                'category': 'structural',
                'description': 'Reinforcement Steel Y12',
                'quantity': 1000,
                'unit_price': 0.0,
                'confidence_score': 0.7,
            })],
        })
        boq.action_pricelist_check()
        self.assertTrue(boq.line_ids[0].product_id)
        self.assertEqual(boq.line_ids[0].unit_price, 1.25)
        self.assertIn(boq.price_check_state, ('matched', 'partial'))

    # ------------------------------------------------------------------ #
    # File validation tests (the common BOQ AI 400 errors)
    # ------------------------------------------------------------------ #
    def test_validator_accepts_real_pdf(self):
        # minimal valid PDF (objects + xref + trailer)
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 0/Kids[]>>endobj\n"
            b"xref\n0 3\n0000000000 65535 f \n"
            b"0000000009 00000 n \n0000000052 00000 n \n"
            b"trailer<</Size 3/Root 1 0 R>>\n"
            b"startxref\n95\n%%EOF\n"
        )
        b64 = base64.b64encode(pdf_bytes)
        svc = self.env['ai.boq.service']
        kind, raw, clean = svc._validate_and_classify(b64, 'plan.pdf')
        self.assertEqual(kind, 'pdf')
        self.assertTrue(raw.startswith(b'%PDF-'))

    def test_validator_rejects_html_renamed_to_pdf(self):
        bad = base64.b64encode(b"<html><body>not a pdf</body></html>")
        svc = self.env['ai.boq.service']
        with self.assertRaises(UserError) as ctx:
            svc._validate_and_classify(bad, 'fake.pdf')
        self.assertIn('not a valid PDF', str(ctx.exception))

    def test_validator_rejects_double_encoded(self):
        # double-base64-encode a valid PDF
        pdf_bytes = b"%PDF-1.4\n%fake\n%%EOF"
        once = base64.b64encode(pdf_bytes)
        twice = base64.b64encode(once)
        svc = self.env['ai.boq.service']
        with self.assertRaises(UserError):
            svc._validate_and_classify(twice, 'plan.pdf')

    def test_validator_accepts_png(self):
        png = self.png_b64
        svc = self.env['ai.boq.service']
        kind, raw, clean = svc._validate_and_classify(png, 'plan.png')
        self.assertEqual(kind, 'image')
