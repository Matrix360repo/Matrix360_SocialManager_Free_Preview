"""Image lab: Director approval and cost barriers without making real API calls."""
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from security_roles import activate_actor, clear_actor
from reference_image_lab import generate_reference_image, approved_reference, view_proof

class ReferenceImageLabTests(unittest.TestCase):
    def test_director_cannot_bypass_site_layout_lock(self):
        token=activate_actor('Director')
        try:
            with patch('reference_image_lab.approved_reference') as ref:
                with self.assertRaises(HTTPException) as ex:
                    generate_reference_image('00000000-0000-0000-0000-000000000001',
                        'Make the entrance prettier with extra greenery',consent='one_paid_image')
                self.assertEqual(ex.exception.status_code,409)
                self.assertIn('suspended',str(ex.exception.detail))
                ref.assert_not_called()
        finally:
            clear_actor(token)

    def test_operator_cannot_generate_paid_image(self):
        token=activate_actor('operator')
        try:
            with self.assertRaises(HTTPException) as ex:
                generate_reference_image('any', 'An industrial development creative', consent='one_paid_image')
            self.assertEqual(ex.exception.status_code,403)
        finally:
            clear_actor(token)

    def test_director_cannot_generate_without_explicit_consent(self):
        token=activate_actor('Director')
        try:
            with self.assertRaises(HTTPException) as ex:
                generate_reference_image('any', 'An industrial development creative')
            self.assertEqual(ex.exception.status_code,409)
        finally:
            clear_actor(token)

    def test_expensive_quality_is_disabled(self):
        token=activate_actor('Director')
        try:
            with self.assertRaises(HTTPException) as ex:
                generate_reference_image('any','An industrial development creative',
                                         quality='high',consent='one_paid_image')
            self.assertEqual(ex.exception.status_code,409)
        finally:
            clear_actor(token)

    def test_bad_asset_id(self):
        with self.assertRaises(HTTPException) as ex:
            approved_reference('path-traversal')
        self.assertEqual(ex.exception.status_code,404)

    def test_bad_proof_id(self):
        with self.assertRaises(HTTPException) as ex:
            view_proof('../secret')
        self.assertEqual(ex.exception.status_code,404)

    def test_missing_key_does_not_trigger_api(self):
        token=activate_actor('Director')
        try:
            with patch('reference_image_lab.approved_reference') as ref:
                with patch.dict('os.environ',{'OPENAI_API_KEY':''}):
                    with self.assertRaises(HTTPException) as ex:
                        generate_reference_image('00000000-0000-0000-0000-000000000001',
                           'An architectural conceptual view of industrial development',
                           consent='one_paid_image')
                    self.assertEqual(ex.exception.status_code,409)
                    ref.assert_not_called()
        finally:
            clear_actor(token)
