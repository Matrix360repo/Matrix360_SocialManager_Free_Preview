import unittest
from unittest.mock import patch
import production_video_import as importer

class VerifiedProviderVideoTests(unittest.TestCase):
 def test_rejects_untrusted_external_video_source(self):
  with patch.dict('os.environ',{'MATRIX_COMPLETED_VIDEO_SOURCE':'https://example.com/fake.mp4'}):
   with self.assertRaisesRegex(RuntimeError,'verified HeyGen'):
    importer.import_reel('4225d6ad-562c-4a63-b334-b9de159e416a')
 def test_existing_verified_video_avoids_duplicate_import(self):
  with patch.dict('os.environ',{'MATRIX_COMPLETED_VIDEO_SOURCE':'https://resource2.heygen.ai/video/example.mp4'}),patch.object(
   importer.media,'media_record',return_value={'status':'completed'}):
   self.assertEqual(importer.import_reel('4225d6ad-562c-4a63-b334-b9de159e416a'),'already_archived')
