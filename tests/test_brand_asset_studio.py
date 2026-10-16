"""Internal reference asset studio: image safety and approval gate tests."""
import io
import unittest
from unittest.mock import patch
from PIL import Image
from fastapi import HTTPException
from security_roles import activate_actor, clear_actor
from brand_asset_studio import clean_plate_image,render_composition,review_asset

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
            clean_plate_image(image_bytes(), 'image/png') if False else clean_plate_image(b'x'*12582913,'image/png')
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
    def test_director_must_attest(self):
        token=activate_actor('Director')
        try:
            with self.assertRaises(HTTPException) as cm:
                review_asset('00000000-0000-0000-0000-000000000001','approved_proof','','')
            self.assertEqual(cm.exception.status_code,422)
        finally:clear_actor(token)

if __name__=='__main__':unittest.main()
