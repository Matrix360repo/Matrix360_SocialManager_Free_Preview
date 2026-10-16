"""AI Content Studio: no fake AI, no risky approvals or unauthorized decisions."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from security_roles import activate_actor,clear_actor
import director_ai_studio as ai
import reference_grid as grid

def candidate(headline='Choose your next industrial location carefully.'):
    return {'option':1,'headline':headline,'pillar':'Planning','subheadline':'West Bengal industrial location planning',
        'caption':'Consult for manufacturing opportunities. +91 74500 08999 www.lakhotiaindustrialcomplex.com',
        'cta':'Talk to the team','creative_guidance':'Use unchanged verified gate image and typography',
        'objective':'Awareness','platform':'Instagram'}

class AiStudioTests(unittest.TestCase):
    def test_claims_screen(self):
        self.assertTrue(ai.strict_check(candidate())['passed'])
        self.assertFalse(ai.strict_check(candidate('An operational fuel station for every plot'))['passed'])
        self.assertFalse(ai.strict_check(candidate('Guaranteed ROI for investors'))['passed'])
        self.assertFalse(ai.strict_check(candidate('Just 7 km from NH-55'))['passed'])

    def test_operator_cannot_trigger_paid_generation_or_decide(self):
        t=activate_actor('operator')
        try:
            with self.assertRaises(HTTPException) as gen:
                ai.create_ai_batch('Create a clear land consultation campaign','Manufacturing businesses',
                                   'Awareness','Instagram','openai')
            self.assertEqual(gen.exception.status_code,403)
            with self.assertRaises(HTTPException) as approval:
                ai.decide('00000000-0000-0000-0000-000000000001',1,'approved','')
            self.assertEqual(approval.exception.status_code,403)
        finally:clear_actor(t)

    def test_ai_failure_never_falls_back_to_template(self):
        t=activate_actor('Director')
        try:
            with patch.object(ai,'verified_master',return_value=b'master'),patch.object(ai,'get_ai_config',return_value={
                'provider':'openai','model':'mock-model','key':'not-real'
            }),patch.object(ai,'create',side_effect=RuntimeError('Provider offline')):
                with self.assertRaises(HTTPException) as ex:
                    ai.create_ai_batch('Create a safe manufacturing campaign','Manufacturing businesses',
                                       'Awareness','Instagram','openai')
                self.assertEqual(ex.exception.status_code,502)
        finally:clear_actor(t)

    def test_three_ai_items_saved_unapproved_and_role_gated(self):
        t=activate_actor('Director')
        try:
            with tempfile.TemporaryDirectory() as tmp,patch.object(grid,'DB',Path(tmp)/'pilot.sqlite3'),patch.object(
                ai,'verified_master',return_value=b'master'),patch.object(ai,'get_ai_config',return_value={
                    'provider':'openai','model':'mock-model','key':'not-real'}),patch.object(
                ai,'create',return_value=([dict(candidate(),option=i,headline='Planning angle '+str(i)) for i in (1,2,3)],'openai_api')):
                result=ai.create_ai_batch('Create three new approaches for industry','Manufacturing businesses',
                                        'Awareness','Instagram','openai')
                self.assertEqual(result['provider'],'openai_api')
                self.assertEqual(len(result['candidates']),3)
                self.assertEqual(result['publication_status'],'blocked')
                saved=ai.batch_detail(result['id'])
                self.assertEqual(len(saved['checks']),3)
                decision=ai.decide(result['id'],1,'approved','')
                self.assertFalse(decision['publication_authorized'])
                self.assertEqual(ai.batch_detail(result['id'])['reviews']['1']['decision'],'approved')
        finally:clear_actor(t)

    def test_rendered_browser_script_has_valid_javascript_syntax(self):
        import director_demo
        import shutil
        import subprocess
        if shutil.which('node') is None:
            self.skipTest('Node.js not installed for browser script parsing')
        t=activate_actor('Director')
        try:
            with patch.object(director_demo,'verified_master',return_value=b'verified-gate'):
                html=director_demo.director_demo().body.decode('utf-8')
        finally:
            clear_actor(t)
        script=html.split('<script>',1)[1].split('</script>',1)[0]
        with tempfile.TemporaryDirectory() as tmp:
            script_path=Path(tmp)/'director-demo.js'
            script_path.write_text(script,encoding='utf-8')
            result=subprocess.run(['node','--check',str(script_path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("aiForm.addEventListener('submit'",script)

    def test_ai_cards_include_verified_architectural_image_with_fallback(self):
        import director_demo
        token=activate_actor('Director')
        try:
            with patch.object(director_demo,'verified_master',return_value=b'approved-master'):
                page=director_demo.director_demo().body.decode()
        finally:
            clear_actor(token)
        self.assertIn('class="ai-master-image"',page)
        self.assertIn('ai-visual-footer',page)
        self.assertIn('Approved architectural visual unavailable',page)
        self.assertIn('src="/api/director-demo/gate"',page)
        self.assertIn('onerror="this.hidden=true;this.nextElementSibling.hidden=false"',page)

    def test_image_endpoint_returns_unmodified_original(self):
        import director_demo
        original=b'checksum-verified-test-master'
        with patch.object(director_demo,'verified_master',return_value=original):
            response=director_demo.architectural_image()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.media_type,'image/png')
        self.assertEqual(response.body,original)

    def test_ui_contains_real_generate_control(self):
        import director_demo
        t=activate_actor('Director')
        try:
            with patch.object(director_demo,'verified_master',return_value=b'test'):
                html=director_demo.director_demo().body.decode()
            self.assertIn('id="ai-form"',html)
            self.assertIn('/api/director-demo/ai/generate',html)
            self.assertIn('Generate 3 AI concepts',html)
        finally:clear_actor(t)
