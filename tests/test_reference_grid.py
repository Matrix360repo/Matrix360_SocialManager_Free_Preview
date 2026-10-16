"""Safety guarantees for the Lakhotia immutable architectural master registry."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from PIL import Image
from security_roles import activate_actor, clear_actor
import reference_grid as grid

def example_png():
    buf=io.BytesIO();Image.new('RGB',(900,650),'#cccccc').save(buf,format='PNG')
    return buf.getvalue()

class ReferenceGridTests(unittest.TestCase):
    def test_wrong_gate_is_rejected_even_if_it_looks_like_a_gate(self):
        with self.assertRaises(HTTPException) as ctx:
            grid.validate_image(example_png(),grid.GATE_NAME,'locked_gate_master')
        self.assertEqual(ctx.exception.status_code,409)

    def test_other_reference_does_not_become_a_gate_master(self):
        digest=grid.validate_image(example_png(),'shed.png','industrial_unit_reference')
        self.assertEqual(len(digest),64)

    def test_corrupted_bytes_and_unsupported_class_rejected(self):
        for raw,role in [(b'bogus','marketing_reference'),(example_png(),'invented_master')]:
            with self.assertRaises(HTTPException):
                grid.validate_image(raw,'image.png',role)

    def test_operator_cannot_change_reference_approval(self):
        token=activate_actor('operator')
        try:
            with self.assertRaises(HTTPException) as ctx:
                grid.review_reference('00000000-0000-0000-0000-000000000001','approved_reference')
            self.assertEqual(ctx.exception.status_code,403)
        finally:
            clear_actor(token)

    def test_director_cannot_approve_locked_reference_by_review_endpoint(self):
        token=activate_actor('Director')
        try:
            with tempfile.TemporaryDirectory() as temp:
                with patch.object(grid,'DB',Path(temp)/'db.sqlite3'):
                    with grid.dbconn() as db:
                        db.execute('INSERT INTO reference_grid VALUES(?,?,?,?,?,?,?,?,?)',
                           ('00000000-0000-0000-0000-000000000001','today',
                            grid.GATE_NAME,grid.GATE_SHA,'locked_gate_master',
                            'pending_review','','source',1))
                        db.commit()
                    with self.assertRaises(HTTPException) as ctx:
                        grid.review_reference('00000000-0000-0000-0000-000000000001','approved_reference')
                    self.assertEqual(ctx.exception.status_code,409)
        finally:clear_actor(token)

    def test_tampered_original_is_blocked(self):
        token=activate_actor('Director')
        try:
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp)
                ident='00000000-0000-0000-0000-000000000001'
                with patch.object(grid,'DB',root/'db.sqlite3'),patch.object(grid,'STORE',root):
                    with grid.dbconn() as db:
                        db.execute('INSERT INTO reference_grid VALUES(?,?,?,?,?,?,?,?,?)',
                            (ident,'today','shed.png','bad-checksum','industrial_unit_reference',
                             'approved_reference','','source',1))
                        db.commit()
                    (root/(ident+'.png')).write_bytes(example_png())
                    with self.assertRaises(HTTPException) as ctx:
                        grid.source_original(ident)
                    self.assertEqual(ctx.exception.status_code,409)
        finally:clear_actor(token)
