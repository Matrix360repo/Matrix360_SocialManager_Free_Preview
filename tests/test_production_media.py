"""Production AI media regression: no fake renders, real bytes, secure routes."""
import io, unittest
from unittest.mock import patch
from fastapi import HTTPException
from PIL import Image
from security_roles import activate_actor,clear_actor
import production_media as p
import production_dashboard as ui

class ProductionMediaTests(unittest.TestCase):
    def test_three_distinct_live_provider_prompts(self):
        concepts=[{'headline':'A unique theme '+str(i),'creative_guidance':'Angle '+str(i)} for i in (1,2,3)]
        prompts=[p.visual_prompt(c,i) for i,c in enumerate(concepts,1)]
        self.assertEqual(len(set(prompts)),3)
        self.assertTrue(all('No text' in x for x in prompts))
        self.assertTrue(all('never' in x.lower() or 'not' in x.lower() for x in prompts))

    def test_real_image_bytes_composed_in_four_platform_sizes(self):
        sample=Image.new('RGB',(300,400),'#778898')
        b=io.BytesIO();sample.save(b,format='PNG')
        c={'headline':'Plan a responsible industrial expansion',
           'subheadline':'Warehouse and manufacturing requirements'}
        outputs=[]
        for platform,size in p.SIZES.items():
            png=p.composite(b.getvalue(),c,platform)
            outputs.append(png)
            with Image.open(io.BytesIO(png)) as img:
                self.assertEqual(img.size,size)
        self.assertEqual(len(set(outputs)),4)

    def test_no_unrendered_video_download(self):
        with patch.object(p,'batch_data',return_value={'reels':[{}, {}, {}]}),patch.object(
             p,'media_record',return_value={'status':'processing','provider_job_id':'vid_something'}):
            with self.assertRaises(HTTPException) as err:
                p.downloadable_reel('00000000-0000-0000-0000-000000000002',1)
            self.assertEqual(err.exception.status_code,409)

    def test_unknown_object_cannot_be_downloaded(self):
        with self.assertRaises(HTTPException) as err:p.download_media('../private-secrets')
        self.assertEqual(err.exception.status_code,404)

    def test_real_model_video_requests_only(self):
        prompts=[p.video_prompt({'video_prompt':'Generic trucks drive through a loading depot, slow drone tracking camera, workers moving real stock.'+str(i)}) for i in range(3)]
        self.assertEqual(len(set(prompts)),3)
        self.assertTrue(all('No posters' in v for v in prompts))

    def test_dashboard_is_production_only(self):
        t=activate_actor('Director')
        try: html=ui.production_studio().body.decode()
        finally:clear_actor(t)
        self.assertIn('/api/production-media/',html)
        self.assertIn('Generate 3 posts + 3 motion reels',html)
        self.assertNotIn('industrial-foundations',html)
        self.assertNotIn('/api/social-posts/',html)
        self.assertIn('video.controls=true',html)
