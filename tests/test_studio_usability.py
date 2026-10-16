"""Operator usability regression for campaign studio POST -> review redirect."""
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from campaign_studio_poc import create_from_studio

class StudioUsabilityTests(unittest.TestCase):
    @patch('app.generate')
    def test_successful_generation_redirects_to_review(self, mock_generate):
        mock_generate.return_value={'id':'1f16c90b-a5b6-4b6d-9d14-a46946028f33',
                                    'status':'review','provider':'offline_template'}
        response=create_from_studio('Industrial expansion planning',
                                    'Consultation enquiries','Instagram','offline')
        self.assertIsInstance(response,RedirectResponse)
        self.assertEqual(response.status_code,303)
        self.assertEqual(response.headers['location'],
                         '/draft/1f16c90b-a5b6-4b6d-9d14-a46946028f33')
        mock_generate.assert_called_once_with(
            topic='Industrial expansion planning',objective='Consultation enquiries',
            platform='Instagram',provider='offline')
    def test_invalid_input_does_not_generate(self):
        for platform,provider in [('Twitter','offline'),('Instagram','unknown')]:
            with self.subTest(platform=platform,provider=provider):
                with self.assertRaises(HTTPException) as err:
                    create_from_studio('Industrial expansion planning',
                                       'Consultation enquiries',platform,provider)
                self.assertEqual(err.exception.status_code,422)
    @patch('app.generate',return_value={'id':'not-a-uuid'})
    def test_invalid_generate_result_rejected(self,_mock):
        with self.assertRaises(HTTPException) as err:
            create_from_studio('Industrial expansion planning',
                               'Consultation enquiries','Instagram','offline')
        self.assertEqual(err.exception.status_code,502)

if __name__=='__main__': unittest.main()
