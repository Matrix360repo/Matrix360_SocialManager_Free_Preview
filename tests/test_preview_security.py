"""Baseline security checks for the disposable Matrix360 preview.

Run: python -m unittest discover -s tests -v
These checks do not establish client-ready authorization or durable storage.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class PreviewSecurityBaseline(unittest.TestCase):
    def test_deployment_seed_files(self):
        for rel in ("app.py", "engine.py", "cloud_start.py", "Dockerfile",
                    "data/brand_profile.json", "assets/lakhotia_group_logo_official.png"):
            with self.subTest(path=rel):
                self.assertTrue((ROOT / rel).is_file(), rel)

    def test_preview_is_explicitly_ephemeral(self):
        startup = (ROOT / "cloud_start.py").read_text(encoding="utf-8")
        self.assertIn("MATRIX360_FREE_PREVIEW", startup)
        self.assertIn("MATRIX360_API_KEY", startup)

    def test_root_gitignore_rejects_sensitive_files(self):
        rules = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (".env", "*.sqlite3"):
            self.assertIn(pattern, rules)

    def test_approval_remains_blocked_for_client_release(self):
        """Current typed reviewer approval is unsafe for multiuser deployment.

        This intentional failing safety gate cannot be bypassed by claiming
        Basic authentication alone authenticates the Director.
        """
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("reviewer':reviewer,'note':'Reviewer identity is self-declared", app,
                         "BLOCKER: approvals still use self-declared identity")
        self.assertNotIn('placeholder="Reviewer name"', app,
                         "BLOCKER: review form accepts arbitrary identity")

if __name__ == "__main__":
    unittest.main()
