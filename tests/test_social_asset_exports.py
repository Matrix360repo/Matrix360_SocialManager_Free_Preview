"""Twelve real downloadable social images across four platforms."""
import io
import unittest
from unittest.mock import patch
from PIL import Image
from fastapi import HTTPException
from security_roles import activate_actor,clear_actor
import social_asset_exports as output

class ChannelAssetTests(unittest.TestCase):
    def test_four_platform_sizes_three_visual_directions(self):
        token=activate_actor('Director')
        try:
            # Image 1 uses exact verified gate; 2 and 3 must not access it.
            sample=Image.new('RGB',(1100,700),'#dddccc')
            master=io.BytesIO();sample.save(master,format='PNG')
            with patch.object(output,'verified_master',return_value=master.getvalue()):
                fingerprints=set()
                for platform,size in output.SIZES.items():
                    for option in (1,2,3):
                        png=output.image_bytes(option,platform)
                        self.assertGreater(len(png),1000)
                        with Image.open(io.BytesIO(png)) as image:
                            self.assertEqual(image.size,size)
                        if platform=='Instagram':fingerprints.add(png)
            self.assertEqual(len(fingerprints),3)
        finally:clear_actor(token)

    def test_operator_cannot_download(self):
        token=activate_actor('operator')
        try:
            with self.assertRaises(HTTPException) as err:
                output.platform_post('Instagram',1)
            self.assertEqual(err.exception.status_code,403)
        finally:clear_actor(token)

    def test_ai_post_uses_generated_headline_not_template(self):
        token=activate_actor('Director')
        try:
            sample=Image.new('RGB',(500,400))
            source=io.BytesIO();sample.save(source,format='PNG')
            with patch.object(output,'verified_master',return_value=source.getvalue()):
                original=output.image_bytes(1,'Instagram')
                changed=output.image_bytes(1,'Instagram','A new approved concept headline')
                self.assertNotEqual(original,changed)
        finally:clear_actor(token)
