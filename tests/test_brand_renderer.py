"""Brand renderer smoke/regression proof: all 3 families render, assets retained."""
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageChops
from brand_renderer_v14 import render_card_v14
from visual_layouts_v12 import render as render_revision

class BrandRendererTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.candidate={
            'headline':'Industrial land planned for growth',
            'subheadline':'Industrial planning in Howrah',
            'caption':'Lakhotia Industrial Complex in Howrah. Call +91 74500 08999 www.lakhotiaindustrialcomplex.com',
            'cta':'Request consultation'
        }
    def test_three_distinct_new_campaign_layouts(self):
        images=[]
        for kind in range(3):
            path=self.base/f'draft_{kind}.png'
            render_card_v14(self.candidate,path,kind)
            with Image.open(path) as png:
                self.assertEqual(png.size,(1080,1350))
                images.append(png.convert('RGB').copy())
        for i in range(3):
            for j in range(i+1,3):
                self.assertIsNotNone(ImageChops.difference(images[i],images[j]).getbbox())
    def test_revisions_use_brand_renderer(self):
        for mode in ('editorial_split','bold_typography','planning_infographic'):
            path=self.base/f'{mode}.png'
            render_revision(self.candidate,path,mode)
            with Image.open(path) as im:self.assertEqual(im.size,(1080,1350))
    def test_long_headline_rejected_instead_of_cut_off(self):
        bad=dict(self.candidate,headline='Long and unsupported headline '*20)
        with self.assertRaises(ValueError):
            render_card_v14(bad,self.base/'bad.png',0)
        self.assertFalse((self.base/'bad.png').exists())

if __name__=='__main__':unittest.main()
