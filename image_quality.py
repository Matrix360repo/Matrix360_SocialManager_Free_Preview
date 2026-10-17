"""Real multimodal inspection of generated industry photographs.

Review for model artefacts before archiving finished client-facing imagery.
The approved architectural master is verified independently and never edited.
"""
import base64
import io
import json
import os
from PIL import Image

class ImageInspectionError(RuntimeError):pass

def inspect_photo(client,raw,index):
    if index not in (2,3):
        raise ImageInspectionError('Only newly generated human/utility photography may be inspected')
    with Image.open(io.BytesIO(raw)) as image:
        preview=image.convert('RGB')
        preview.thumbnail((640,960),Image.Resampling.LANCZOS)
        buffer=io.BytesIO()
        preview.save(buffer,format='JPEG',quality=74,optimize=True)
    encoded=base64.b64encode(buffer.getvalue()).decode('ascii')
    specific=(
       'Review one or two adult people in a realistic industrial workplace. '
       'Look for repeated cloned faces, extra people, malformed hands, '
       'extra fingers, duplicated limbs, double heads, odd disconnected '
       'objects, plastic skin, inconsistent shadows or pasted photographs.'
       if index==2 else
       'Review a realistic person-free industrial technology scene. '
       'Reject people, duplicated instrument panels, inconsistent pipes '
       'or cable connections, nonsensical technology or physical impossibility.'
    )
    try:
        response=client.chat.completions.create(
          model=os.getenv('MATRIX_IMAGE_REVIEW_MODEL','gpt-4.1-mini'),
          response_format={'type':'json_object'},
          messages=[
           {'role':'system','content':(
             'You are a strict professional photographic quality-control '
             'inspector. Answer only JSON with boolean approved and array '
             'issues containing precise visible defects. '
             'Assess spatial and anatomical realism, geometry, consistency, '
             'duplication and artifact-free client-presentation quality. '
             'Approve genuinely coherent photography even if it is generic. '
             'Never claim a pictured facility exists at Lakhotia.'
           )},
           {'role':'user','content':[
             {'type':'text','text':specific},
             {'type':'image_url','image_url':{
               'url':'data:image/jpeg;base64,'+encoded,'detail':'low'}}
           ]}
          ],
          temperature=0,
          timeout=40)
        result=json.loads(response.choices[0].message.content)
    except Exception as exc:
        raise ImageInspectionError('Photo inspector unavailable: '+type(exc).__name__) from None
    if not isinstance(result,dict) or not isinstance(result.get('approved'),bool):
        raise ImageInspectionError('Photo inspector returned invalid evaluation')
    findings=result.get('issues',[])
    if not isinstance(findings,list):
        raise ImageInspectionError('Photo inspector reported invalid issues')
    issues=[str(x)[:110] for x in findings[:5]]
    return {'approved':result['approved'] and not issues,'issues':issues}
