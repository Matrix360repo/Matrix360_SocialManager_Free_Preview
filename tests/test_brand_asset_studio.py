"""Internal reference asset studio: image safety and approval gate tests."""
import io
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image
from fastapi import HTTPException
from security_roles import activate_actor, clear_actor
from brand_asset_studio import clean_plate_image,render_composition,review_asset,candidate_brand_proof
import brand_asset_studio as studio

def image_bytes(fmt='PNG',size=(1200,800)):
    im=Image.new('RGB',size,'#d6ddd9');buf=io.BytesIO();im.save(buf,fmt);return buf.getvalue()

class AssetStudioTests(unittest.TestCase):
    def test_valid_clean_plate_is_normalized(self):
        content,dimensions=clean_plate_image(image_bytes(), 'image/png')
        self.assertEqual(dimensions,(1200,800))
        with Image.open(io.BytesIO(content)) as im:
            self.assertEqual(im.format,'PNG')
    def test_bogus_extension_and_oversize_rejected(self):
        with self.assertRaises(HTTPException):
            clean_plate_image(b'not png', 'image/png')
        with self.assertRaises(HTTPException):
            clean_plate_image(image_bytes('JPEG'), 'image/gif')
        with self.assertRaises(HTTPException):
            clean_plate_image(b'x'*12582913,'image/png')
    def test_small_images_rejected(self):
        with self.assertRaises(HTTPException):
            clean_plate_image(image_bytes(size=(800,500)), 'image/png')
    def test_proof_has_expected_size_and_logo(self):
        pixels=Image.new('RGB',(1200,800),'#b8cfd0')
        data=render_composition(pixels)
        with Image.open(io.BytesIO(data)) as im:self.assertEqual(im.size,(1080,1350))
    def test_operator_cannot_approve(self):
        token=activate_actor('operator')
        try:
            with self.assertRaises(HTTPException) as cm:
                review_asset('00000000-0000-0000-0000-000000000001','approved_proof','clean_plate','')
            self.assertEqual(cm.exception.status_code,403)
        finally:clear_actor(token)
    def test_campaign_proof_authorization_and_existing_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);data_path=tmp/'proof.sqlite3';asset_dir=tmp/'clean';asset_dir.mkdir()
            asset_id='00000000-0000-0000-0000-000000000001'
            draft_id='00000000-0000-0000-0000-000000000002'
            im=Image.new('RGB',(1200,800),'#d6ddd9')
            im.save(asset_dir/f'{asset_id}.png')
            candidate={'option':1,'headline':'Land planned for business growth',
              'caption':'Lakhotia Industrial Complex on Ranihati–Amta Road, Howrah. '
                        'Call +91 74500 08999 www.lakhotiaindustrialcomplex.com',
              'cta':'Discuss your land requirement'}
            with sqlite3.connect(data_path) as db:
                db.execute('CREATE TABLE brand_assets(id TEXT,status TEXT)')
                db.execute('CREATE TABLE drafts(id TEXT,payload TEXT,checks TEXT,status TEXT)')
                db.execute('INSERT INTO brand_assets VALUES(?,?)',(asset_id,'pending'))
                db.execute('INSERT INTO drafts VALUES(?,?,?,?)',
                    (draft_id,json.dumps([candidate,
                      {'option':2},{'option':3}]),
                     json.dumps([{'option':1,'passed':True},
                       {'option':2,'passed':True},{'option':3,'passed':True}]),'review'))
                db.commit()
            with patch.object(studio,'DB',data_path),patch.object(studio,'DIR',asset_dir):
                with self.assertRaises(HTTPException) as e:
                    candidate_brand_proof(asset_id,draft_id,1)
                self.assertEqual(e.exception.status_code,403)
                with sqlite3.connect(data_path) as db:
                    db.execute('UPDATE brand_assets SET status=?',('approved_proof',))
                    db.commit()
                proof=candidate_brand_proof(asset_id,draft_id,1)
                self.assertEqual(proof.media_type,'image/png')
                self.assertEqual(proof.headers['X-Matrix360-Asset-Status'],'internal-proof-only')
                with Image.open(io.BytesIO(proof.body)) as rendered:
                    self.assertEqual(rendered.size,(1080,1350))
                # Rejected / nonreview draft must not generate proofs.
                with sqlite3.connect(data_path) as db:
                    db.execute('UPDATE drafts SET status=?',('approved',))
                    db.commit()
                with self.assertRaises(HTTPException) as e:
                    candidate_brand_proof(asset_id,draft_id,1)
                self.assertEqual(e.exception.status_code,409)
    def test_invalid_campaign_preview_inputs_fail(self):
        with self.assertRaises(HTTPException) as e:
            candidate_brand_proof('bad','also-bad',1)
        self.assertEqual(e.exception.status_code,404)
        with self.assertRaises(HTTPException) as e:
            candidate_brand_proof('bad','also-bad',4)
        self.assertEqual(e.exception.status_code,404)
    def test_director_must_attest(self):
        token=activate_actor('Director')
        try:
            with self.assertRaises(HTTPException) as cm:
                review_asset('00000000-0000-0000-0000-000000000001','approved_proof','','')
            self.assertEqual(cm.exception.status_code,422)
        finally:clear_actor(token)

if __name__=='__main__':unittest.main()
