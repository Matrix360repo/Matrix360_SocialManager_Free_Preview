"""Regression: verified architectural master persists across missing DB and file."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
import reference_grid as grid
import reference_persistence as storage

class ReferenceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.raw=b'fake-source-for-isolated-unit-test'
        self.sha=hashlib.sha256(self.raw).hexdigest()

    def test_no_config_is_explicitly_ephemeral(self):
        with patch.dict('os.environ',{
            'MATRIX_REFERENCE_SUPABASE_URL':'',
            'MATRIX_REFERENCE_SUPABASE_BUCKET':'',
            'MATRIX_REFERENCE_SUPABASE_SERVICE_KEY':''}):
            self.assertIsNone(storage.settings())
            self.assertFalse(storage.backup_gate(self.raw) if self.sha==storage.GATE_SHA else self._with_sha_backup())

    def _with_sha_backup(self):
        with patch.object(storage,'GATE_SHA',self.sha):
            return storage.backup_gate(self.raw)

    def test_missing_credentials_fail_closed(self):
        with patch.dict('os.environ',{'MATRIX_REFERENCE_SUPABASE_URL':'https://example.supabase.co',
                                     'MATRIX_REFERENCE_SUPABASE_BUCKET':'private-assets',
                                     'MATRIX_REFERENCE_SUPABASE_SERVICE_KEY':''}):
            with self.assertRaises(storage.StorageError):
                storage.settings()

    def test_wrong_remote_bytes_are_rejected(self):
        with patch.object(storage,'GATE_SHA',self.sha):
            with patch.object(storage,'_request',return_value=b'wrong'):
                with self.assertRaises(storage.StorageError):
                    storage.fetch_gate()

    def test_backup_refuses_remote_collision(self):
        with patch.object(storage,'GATE_SHA',self.sha),patch.object(storage,'settings',return_value=('https://test.supabase.co','private','token')):
            with patch.object(storage,'_request',return_value=b'not-the-master'):
                with self.assertRaises(storage.StorageError):
                    storage.backup_gate(self.raw)

    def test_restore_from_remote_recreates_approved_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with patch.object(grid,'DB',base/'data.sqlite3'),patch.object(grid,'STORE',base/'images'),patch.object(grid,'GATE_SHA',self.sha),patch.object(storage,'GATE_SHA',self.sha),patch.object(storage,'settings',return_value=('https://test.supabase.co','private','token')),patch.object(storage,'fetch_gate',return_value=self.raw):
                self.assertTrue(grid.restore_gate_record())
                with grid.dbconn() as db:
                    row=db.execute('SELECT id,sha256,status,role FROM reference_grid').fetchone()
                self.assertEqual(row[1:],(self.sha,'verified','locked_gate_master'))
                self.assertEqual((grid.STORE/(row[0]+'.png')).read_bytes(),self.raw)
                # Simulate ephemeral loss of file only: restore the same ID.
                (grid.STORE/(row[0]+'.png')).unlink()
                self.assertTrue(grid.restore_gate_record())
                with grid.dbconn() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM reference_grid').fetchone()[0],1)
                self.assertEqual((grid.STORE/(row[0]+'.png')).read_bytes(),self.raw)

    def test_no_false_verification_when_remote_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            with patch.object(grid,'DB',base/'db.sqlite3'),patch.object(grid,'STORE',base/'images'),patch.object(storage,'settings',return_value=('https://test.supabase.co','private','token')),patch.object(storage,'fetch_gate',side_effect=storage.StorageError('offline')):
                self.assertFalse(grid.restore_gate_record())
                with grid.dbconn() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM reference_grid').fetchone()[0],0)
