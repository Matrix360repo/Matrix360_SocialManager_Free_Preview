"""October pilot security regression tests. Run python -m unittest discover -s tests -v."""
import base64
import os
import pathlib
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from security_roles import activate_actor, clear_actor, configured, resolve_actor, director_required

ROOT=pathlib.Path(__file__).resolve().parents[1]
OP="o"*40
DIRECTOR="d"*40

class PreviewSecurityBaseline(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ, {"MATRIX360_API_KEY":OP,"MATRIX360_DIRECTOR_KEY":DIRECTOR})
        self.env.start()
    def tearDown(self):
        self.env.stop()
    def basic(self, user, password):
        token=base64.b64encode(f"{user}:{password}".encode()).decode()
        return {"Authorization":"Basic "+token}
    def test_seed_files(self):
        for rel in ("app.py","engine.py","cloud_start.py","Dockerfile","data/brand_profile.json","assets/lakhotia_group_logo_official.png"):
            with self.subTest(file=rel):self.assertTrue((ROOT/rel).is_file(),rel)
    def test_missing_or_same_director_key_fails_closed(self):
        with patch.dict(os.environ, {"MATRIX360_DIRECTOR_KEY":""}):
            self.assertFalse(configured())
        with patch.dict(os.environ, {"MATRIX360_DIRECTOR_KEY":OP}):
            self.assertFalse(configured())
    def test_role_credentials_not_interchangeable(self):
        self.assertTrue(configured())
        self.assertEqual(resolve_actor(self.basic("operator",OP)),"operator")
        self.assertEqual(resolve_actor(self.basic("director",DIRECTOR)),"Director")
        self.assertIsNone(resolve_actor(self.basic("director",OP)))
        self.assertIsNone(resolve_actor(self.basic("operator",DIRECTOR)))
        self.assertIsNone(resolve_actor(self.basic("anyname",OP)))
    def test_header_roles(self):
        self.assertEqual(resolve_actor({"X-Matrix360-Key":OP}),"operator")
        self.assertEqual(resolve_actor({"X-Matrix360-Director-Key":DIRECTOR}),"Director")
    def test_director_permission(self):
        for role in (None,"operator"):
            token=activate_actor(role)
            try:
                with self.assertRaises(HTTPException) as error:director_required()
                self.assertEqual(error.exception.status_code,403)
            finally:clear_actor(token)
        token=activate_actor("Director")
        try:self.assertEqual(director_required(),"Director")
        finally:clear_actor(token)
    def test_all_approval_entrypoints_have_director_check(self):
        files=("app.py","review_addon.py","revision_agent.py")
        for filename in files:
            source=(ROOT/filename).read_text(encoding="utf-8")
            self.assertIn("director_required()",source,filename)
        self.assertIn("reviewer=director_required()", (ROOT/"review_addon.py").read_text(encoding="utf-8"))
        self.assertIn("reviewer=director_required()", (ROOT/"revision_agent.py").read_text(encoding="utf-8"))
    def test_approval_metadata_no_longer_declared_self(self):
        for file in ("app.py","review_addon.py","revision_agent.py"):
            source=(ROOT/file).read_text(encoding="utf-8")
            self.assertNotIn("'approved_by_self_declared_reviewer'",source)
    def test_secret_files_gitignored(self):
        rules=(ROOT/".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env",rules)
        self.assertIn("*.sqlite3",rules)

if __name__=="__main__":unittest.main()
