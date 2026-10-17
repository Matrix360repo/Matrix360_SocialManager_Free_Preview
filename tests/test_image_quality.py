import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from PIL import Image
from image_quality import inspect_photo,ImageInspectionError

class VisionGateTests(unittest.TestCase):
 def sample(self):
  i=Image.new('RGB',(80,100))
  b=io.BytesIO();i.save(b,format='PNG')
  return b.getvalue()
 def test_good_image(self):
  client=Mock()
  client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"approved":true,"issues":[]}'))])
  self.assertTrue(inspect_photo(client,self.sample(),2)['approved'])
 def test_bad_image(self):
  client=Mock()
  client.chat.completions.create.return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"approved":false,"issues":["visual defect"]}'))])
  self.assertFalse(inspect_photo(client,self.sample(),3)['approved'])

 def test_operator_may_not_regenerate_photography(self):
  from fastapi import HTTPException
  from security_roles import activate_actor,clear_actor
  import production_media as media
  actor=activate_actor('operator')
  try:
   with self.assertRaises(HTTPException) as error:
    media.regenerate_photo('00000000-0000-0000-0000-000000000123',2)
   self.assertEqual(error.exception.status_code,403)
  finally:clear_actor(actor)
