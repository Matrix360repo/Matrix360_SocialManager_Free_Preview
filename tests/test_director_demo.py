"""October 16 Director demo: architecture, storyboard, CTA and release-gate."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from security_roles import activate_actor, clear_actor
import director_demo as demo
import reference_grid as grid

class DirectorDemoTests(unittest.TestCase):
    def test_three_distinct_compliant_concepts(self):
        self.assertEqual(len(demo.CONCEPTS),3)
        self.assertEqual(len({x['title'] for x in demo.CONCEPTS}),3)
        for c in demo.CONCEPTS:
            self.assertNotIn('ready now',str(c).lower())
            self.assertNotIn('operational fuel',str(c).lower())

    def test_verified_master_failure_is_fail_closed(self):
        with patch.object(grid,'restore_gate_record',return_value=False):
            with self.assertRaises(HTTPException) as ctx:
                demo.verified_master()
            self.assertEqual(ctx.exception.status_code,503)

    def test_storyboard_exactly_thirty_seconds(self):
        plan=demo.director_storyboard()
        self.assertEqual(plan['duration_seconds'],30)
        self.assertEqual(len(plan['scenes']),5)
        self.assertEqual(plan['production_status'],'storyboard_only')

    def test_operator_cannot_approve_or_publish(self):
        tok=activate_actor('operator')
        try:
            with self.assertRaises(HTTPException) as ctx:
                demo.review_concept(1,'approved','')
            self.assertEqual(ctx.exception.status_code,403)
            with self.assertRaises(HTTPException) as pub:
                demo.publish_blocked()
            self.assertEqual(pub.exception.status_code,403)
        finally:clear_actor(tok)

    def test_director_can_decide_but_never_publish(self):
        tok=activate_actor('Director')
        try:
            with tempfile.TemporaryDirectory() as tmp:
                with patch.object(grid,'DB',Path(tmp)/'pilot.sqlite3'),patch.object(
                        demo,'verified_master',return_value=b'verified_gate'):
                    r=demo.review_concept(1,'approved','approved for review')
                    self.assertEqual(r['status'],'approved')
                    self.assertFalse(r['publication_authorized'])
                    r=demo.review_concept(2,'rejected','not on brand')
                    self.assertEqual(r['status'],'rejected')
                    states=demo.review_states()
                    self.assertEqual(states['1']['status'],'approved')
                    self.assertEqual(states['2']['status'],'rejected')
                    with demo.dbconn() as db:
                        self.assertEqual(db.execute('select count(*) from director_demo_audit').fetchone()[0],2)
            with self.assertRaises(HTTPException) as ctx:
                demo.publish_blocked()
            self.assertEqual(ctx.exception.status_code,409)
        finally:clear_actor(tok)

    def test_unapproved_architectural_content_never_drawn(self):
        tok=activate_actor('Director')
        try:
            with patch.object(demo,'verified_master',return_value=b'gate bytes'):
                page=demo.director_demo().body.decode()
            self.assertEqual(page.count('class="art art-'),3)
            self.assertEqual(page.split('<script>',1)[0].count('src="/api/director-demo/gate"'),3)
            self.assertIn('production_status',str(demo.director_storyboard()))
            self.assertIn('Publishing is blocked',page)
        finally:clear_actor(tok)
