"""Reference-grid v2 acceptance: geometry never redrawn and batch is fail-closed."""
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
from PIL import Image
from security_roles import activate_actor,clear_actor
import architectural_compositor as compositor
import reference_gallery_v2 as gallery
import reference_grid as grid

def sample():
    out=io.BytesIO()
    im=Image.new('RGB',(1200,800),'#568e8d')
    im.save(out,format='PNG')
    return out.getvalue()

class MasterPreservationTests(unittest.TestCase):
    def setUp(self):self.raw=sample()

    def test_default_wrapped_headline_has_clearance_from_master(self):
        from creative_renderer_v07 import _f
        from PIL import ImageDraw
        canvas=Image.new('RGB',(compositor.W,compositor.H))
        draw=ImageDraw.Draw(canvas)
        text='Land at the right place for your business'
        lines=[];part=''
        for word in text.split():
            maybe=(part+' '+word).strip()
            if draw.textbbox((0,0),maybe,font=_f(46,True))[2]>990 and part:
                lines.append(part);part=word
            else:
                part=maybe
        if part:lines.append(part)
        bottom=max(draw.textbbox((43,166+i*54),line,font=_f(46,True))[3]
                   for i,line in enumerate(lines))
        self.assertGreaterEqual(len(lines),2)
        self.assertGreaterEqual(compositor.PANEL[1]-bottom,28)

    def test_unchanged_original_is_required_for_compositor(self):
        with self.assertRaises(HTTPException) as ex:
            compositor.make_gate_proof(self.raw)
        self.assertEqual(ex.exception.status_code,409)

    def test_verified_source_embedded_at_correct_aspect_ratio(self):
        digest=hashlib.sha256(self.raw).hexdigest()
        with patch.object(grid,'GATE_SHA',digest),patch.object(compositor.grid,'GATE_SHA',digest):
            proof,geometry=compositor.make_gate_proof(self.raw)
        x,y,w,h=geometry
        self.assertAlmostEqual(w/h,1200/800,delta=0.005)
        with Image.open(io.BytesIO(proof)) as output:
            self.assertEqual(output.size,(1080,1350))
            embedded=output.crop((x,y,x+w,y+h))
            expected=Image.open(io.BytesIO(self.raw)).convert('RGB')
            expected.thumbnail((compositor.PANEL[2]-compositor.PANEL[0],
                                compositor.PANEL[3]-compositor.PANEL[1]),Image.Resampling.LANCZOS)
            self.assertEqual(embedded.tobytes(),expected.tobytes())

    def test_original_blob_tampering_is_rejected(self):
        digest=hashlib.sha256(self.raw).hexdigest()
        identifier='00000000-0000-0000-0000-000000000003'
        with tempfile.TemporaryDirectory() as tmp:
            directory=Path(tmp)
            with patch.object(grid,'DB',directory/'db.sqlite3'),patch.object(grid,'STORE',directory),patch.object(grid,'GATE_SHA',digest):
                with grid.dbconn() as db:
                    db.execute('INSERT INTO reference_grid VALUES(?,?,?,?,?,?,?,?,?)',
                               (identifier,'today',grid.GATE_NAME,digest,'locked_gate_master','verified','','library',1))
                    db.commit()
                (directory/(identifier+'.png')).write_bytes(self.raw+b'extra')
                with self.assertRaises(HTTPException) as ex:compositor.load_verified_gate(identifier)
                self.assertEqual(ex.exception.status_code,409)

class GalleryBatchTests(unittest.TestCase):
    def test_operator_cannot_batch_import(self):
        token=activate_actor('operator')
        try:
            with self.assertRaises(HTTPException) as ex:
                gallery.intake_batch([('a.png',sample())],'marketing_reference','library:1','')
            self.assertEqual(ex.exception.status_code,403)
        finally:clear_actor(token)

    def test_batch_cannot_import_gate_master(self):
        token=activate_actor('Director')
        try:
            with self.assertRaises(HTTPException) as ex:
                gallery.intake_batch([('a.png',sample())],'locked_gate_master','library:1','')
            self.assertEqual(ex.exception.status_code,409)
        finally:clear_actor(token)

    def test_bad_batch_rejects_all_without_writes(self):
        token=activate_actor('Director')
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                with patch.object(grid,'DB',root/'test.sqlite3'),patch.object(grid,'STORE',root/'images'):
                    with self.assertRaises(HTTPException):
                        gallery.intake_batch([('valid.png',sample()),('bad.png',b'fake')],
                                            'industrial_unit_reference','library:1','')
                    self.assertFalse((root/'images').exists())
        finally:clear_actor(token)

    def test_two_supporting_references_enter_pending_status(self):
        token=activate_actor('Director')
        try:
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                with patch.object(grid,'DB',root/'test.sqlite3'),patch.object(grid,'STORE',root/'images'):
                    result=gallery.intake_batch([('a.png',sample()),('b.png',sample())],
                                'brand_design_reference','verified-source','layout only')
                    self.assertEqual(result['count'],2)
                    self.assertEqual(result['status'],'pending_review')
                    with grid.dbconn() as db:
                        rows=db.execute('SELECT role,status FROM reference_grid').fetchall()
                    self.assertEqual(rows,[('brand_design_reference','pending_review')]*2)
        finally:clear_actor(token)
