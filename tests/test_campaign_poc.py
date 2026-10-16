"""Deterministic POC checks, no paid AI calls or outbound messages."""
import unittest
from fastapi import HTTPException
from campaign_studio_poc import storyboard, cta_target, CAMPAIGN_ID
class CampaignPOCTests(unittest.TestCase):
    def test_storyboard_has_five_scenes_and_correct_claims(self):
        plan=storyboard("Industrial expansion planning","Instagram","Consultation enquiries")
        self.assertEqual(plan['duration_seconds'],30)
        self.assertEqual(plan['production_status'],'storyboard_only')
        self.assertEqual(plan['status'],'requires_director_approval')
        self.assertEqual(len(plan['scenes']),5)
        content=" ".join(str(s) for s in plan['scenes'])
        self.assertIn("NH-16",content)
        self.assertIn("74500 08999",content)
        self.assertNotIn("800 bighas",content)
        self.assertNotIn("operational fuel station",content)
    def test_tracked_url_is_allowlisted(self):
        url=cta_target(CAMPAIGN_ID)
        self.assertTrue(url.startswith("https://www.lakhotiaindustrialcomplex.com/?"))
        self.assertIn("utm_campaign=lakhotia_poc_consultation",url)
        with self.assertRaises(HTTPException):cta_target("https://bad.example")
    def test_invalid_briefs_rejected(self):
        for platform in ("Twitter","",'<script>'):
            with self.assertRaises(HTTPException):storyboard("Industrial expansion planning",platform,"Awareness")
        with self.assertRaises(HTTPException):storyboard("<script>alert</script>","Instagram","Awareness")
if __name__=="__main__":unittest.main()
