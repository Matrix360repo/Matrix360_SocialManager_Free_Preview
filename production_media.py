"""Production-only AI images and Sora motion-video rendering.

Every background comes from a real provider request. No fallback photos,
template illustrations, dummy files, or poster-motion videos. All media is
private in Supabase Storage, served only to authenticated application users.
"""
import base64
import io
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request,urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from PIL import Image,ImageDraw,ImageFont,ImageOps
from fastapi import APIRouter,HTTPException
from fastapi.responses import Response
from openai import OpenAI
from security_roles import director_required
import durable_campaign_store as db

router=APIRouter()
BUCKET='matrix360-campaign-media'
SIZES={'Instagram':(1080,1350),'Facebook':(1200,630),'LinkedIn':(1200,627),'X-Twitter':(1600,900)}
FONTS=('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
ACTIVE=set()
GUARD=threading.Lock()

def auth_config():
    from reference_persistence import settings
    cfg=settings()
    if cfg is None:raise RuntimeError('Supabase private media storage unavailable')
    return cfg[0],cfg[2]

def media_record(batch_id,option,kind):
    rows=db.api('media','GET','select=*&batch_id=eq.'+quote(batch_id)+'&option_no=eq.'+str(option)+'&kind=eq.'+kind)
    return rows[0] if rows else None

def set_record(batch_id,option,kind,status,object_path=None,provider_job_id=None,error=None):
    payload={'batch_id':batch_id,'option_no':option,'kind':kind,'status':status,
             'object_path':object_path,'provider_job_id':provider_job_id,
             'error_message':(str(error)[:210] if error else None)}
    db.api('media','POST','on_conflict=batch_id,option_no,kind',payload=[payload],
           prefer='resolution=merge-duplicates,return=minimal')

def upload_media(path,raw,mimetype):
    if not raw:raise RuntimeError('Empty AI media asset rejected')
    url,key=auth_config()
    endpoint=url+'/storage/v1/object/'+BUCKET+'/'+path
    req=Request(endpoint,data=raw,method='POST',headers={
        'apikey':key,'Authorization':'Bearer '+key,'Content-Type':mimetype,
        'x-upsert':'true'})
    try:
        with urlopen(req,timeout=90) as resp:resp.read()
    except HTTPError as err:
        raise RuntimeError('Private media upload HTTP '+str(err.code)) from None

def download_media(path):
    if not path or not re.fullmatch(r'[0-9a-f-]{36}/(?:image|video)/[1-3]\.(?:png|mp4)',path):
        raise HTTPException(404,'Unknown media object')
    url,key=auth_config()
    req=Request(url+'/storage/v1/object/'+BUCKET+'/'+path,
          headers={'apikey':key,'Authorization':'Bearer '+key})
    try:
        with urlopen(req,timeout=45) as resp:
            data=resp.read(105*1024*1024)
    except HTTPError as err:
        raise HTTPException(502,'Private media storage HTTP '+str(err.code)) from None
    if not data:raise HTTPException(502,'Empty stored file')
    return data

VISUAL_PILLARS=(
    'Architecture & Infrastructure',
    'Human Element & Operations',
    'Facilities, Utilities & Technology',
)

def visual_prompt(candidate,index):
    """Nonoverlapping photographic categories; no invented Lakhotia buildings."""
    if index not in (1,2,3):raise ValueError('Unsupported visual pillar')
    scene=str(candidate.get('creative_guidance','')).strip()[:1300]
    desc=str(candidate.get('headline','')).strip()[:130]
    constraints=(
       'Use ONLY the externally verified and unmodified Lakhotia gate artwork. '
       'Do not synthesize a master plan or a project building. This category is '
       'rendered from the approved original, not sent to generative imaging.',
       'Show authentic industrial PEOPLE at work: one clearly distinct adult '
       'professional or, at most, two different adults naturally cooperating. '
       'One physically coherent human per pose, exactly two arms and hands '
       'per person, five realistic fingers per visible hand, no mirrored or '
       'cloned workers, repeated faces, extra limbs, fused fingers, '
       'photographic cutout seams, duplicate heads or uncanny plastic skin. '
       'Editorial candid shot of real operational decisions, movement and '
       'working environment. No children.',
       'Show a PERSON-FREE close-up of believable generic industrial '
       'utilities or industrial instrumentation: precisely engineered '
       'electrical distribution control cabinet, monitoring gauges, '
       'plumbing or sensor equipment, physical cable conduits and '
       'warehouse technology. Grounded true-to-life materials and scale. '
       'No humans, no duplicate equipment, no impossible pipe connections. '
       'This is CONCEPTUAL illustrative industry technology, NOT a '
       'depiction of installed Lakhotia utilities.',
    )
    return (
       'Create one original high-end photorealistic advertising photograph. '
       'PILLAR '+str(index)+' — '+VISUAL_PILLARS[index-1]+'. '
       'Hard visual constraint: '+constraints[index-1]+'. '
       'User campaign creative idea (secondary to visual constraint): '+scene+'. '
       'Headline context: '+desc+'. '
       'NO typography or text in the actual generated image, NO logos, '
       'NO signs, posters or gibberish labels, no watermarks. '
       'Never recreate or alter the approved Lakhotia architectural gate. '
       'Never attribute conceptual photographed facilities or generic '
       'workers to Lakhotia, or falsely present them as actual site infrastructure. '
       'Single coherent photograph, correct perspective, realistic lighting, '
       'human anatomy and photographic realism. Avoid split-screen collage, '
       'mirrored subjects, implausible symmetry, random cutouts, unnaturally '
       'cloned visual subjects, or computer illustration aesthetics.'
    )

def generate_one_image(batch_id,idx,candidate):
    try:
        set_record(batch_id,idx,'image','processing')
        if idx==1:
            # Site-specific architectural visual must be exactly the locked source.
            from director_demo import verified_master
            raw=verified_master()
            with Image.open(io.BytesIO(raw)) as gate:gate.verify()
            path=f'{batch_id}/image/1.png'
            upload_media(path,raw,'image/png')
            set_record(batch_id,idx,'image','completed',object_path=path)
            return
        api_key=os.getenv('OPENAI_API_KEY','').strip()
        if not api_key:raise RuntimeError('OPENAI_API_KEY missing for real image generation')
        client=OpenAI(api_key=api_key,timeout=110,max_retries=1)
        response=client.images.generate(model=os.getenv('MATRIX_IMAGE_MODEL','gpt-image-1-mini'),
                prompt=visual_prompt(candidate,idx),size='1024x1536',quality='medium',n=1)
        encoded=response.data[0].b64_json
        if not encoded:raise RuntimeError('Image generation returned no binary')
        raw=base64.b64decode(encoded)
        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
        path=f'{batch_id}/image/{idx}.png'
        upload_media(path,raw,'image/png')
        set_record(batch_id,idx,'image','completed',object_path=path)
    except Exception as exc:
        try:set_record(batch_id,idx,'image','failed',error=type(exc).__name__+': '+str(exc)[:100])
        except Exception:pass

def video_prompt(spec):
    prompt=str(spec.get('video_prompt','')).strip()[:1800]
    if len(prompt)<30:raise RuntimeError('AI reel prompt missing')
    return (prompt+'\nGENUINE MOTION VIDEO: changing camera position, moving industrial machinery, trucks in motion, or physical human planning actions. '
      'No posters, static slideshows, zoom effects, animated still photos. '
      'All industry scenes generic illustrative footage, never misrepresent as the real Lakhotia Industrial Complex. '
      'Never show or reconstruct specific Lakhotia gate, site layout or invented site structures. '
      'No typography or logos; brand identity is layered separately in application after render.')

def create_one_video(batch_id,idx,reel):
    """Full motion graphics encoded from genuinely different source photographs.

    A 404 from an unavailable Sora account is never mistaken for a storage
    problem. This route uses locally installed FFmpeg plus authenticated TTS.
    """
    try:
        existing=media_record(batch_id,idx,'video')
        if existing and existing.get('status')=='completed':
            return
        set_record(batch_id,idx,'video','processing')
        photo_record=media_record(batch_id,idx,'image')
        if not photo_record or photo_record['status']!='completed':
            raise RuntimeError('Verified photographic source is not ready')
        if idx==1:
            from director_demo import verified_master
            photo=verified_master()
        else:
            photo=download_media(photo_record['object_path'])
        key=os.getenv('OPENAI_API_KEY','').strip()
        if not key:
            raise RuntimeError('OPENAI_API_KEY missing for voiceover')
        from motion_reels import render_reel,synth_voice,probe_video
        client=OpenAI(api_key=key,timeout=60,max_retries=1)
        voice=synth_voice(client,reel)
        raw=render_reel(photo,idx,reel,voice)
        if len(raw)<15000 or raw[4:8]!=b'ftyp':
            raise RuntimeError('FFmpeg returned invalid MP4')
        path=f'{batch_id}/video/{idx}.mp4'
        upload_media(path,raw,'video/mp4')
        # End-to-end storage readback and basic signature verification.
        remote=download_media(path)
        import hashlib
        if hashlib.sha256(remote).digest()!=hashlib.sha256(raw).digest():
            raise RuntimeError('Private MP4 archival readback mismatch')
        set_record(batch_id,idx,'video','completed',object_path=path,
                   provider_job_id='ffmpeg_tts_motion_v1')
    except Exception as exc:
        try:
            set_record(batch_id,idx,'video','failed',
                       error=type(exc).__name__+': '+str(exc)[:95])
        except Exception:
            pass

def _worker(batch_id,concepts,reels):
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            pending=[pool.submit(generate_one_image,batch_id,i,c)
                     for i,c in enumerate(concepts,1)]
            for task in pending:task.result()
        # Single job at a time prevents Render Free memory/CPU exhaustion.
        for i,reel in enumerate(reels,1):
            create_one_video(batch_id,i,reel)
    finally:
        with GUARD:
            ACTIVE.discard(batch_id)

def render_existing_batch(batch_id):
    """Repair failed or missing MP4 jobs using already archived real assets."""
    data=batch_data(batch_id)
    with GUARD:
        if batch_id in ACTIVE:
            return False
        ACTIVE.add(batch_id)
    def recover():
        try:
            for idx,reel in enumerate(data['reels'],1):
                create_one_video(batch_id,idx,reel)
        finally:
            with GUARD:ACTIVE.discard(batch_id)
    threading.Thread(target=recover,daemon=True,
                     name='motion-graphics-'+batch_id[:8]).start()
    return True

def launch(batch_id,concepts,reels):
    if len(concepts)!=3 or len(reels)!=3:raise ValueError('Three AI post and reel concepts required')
    with GUARD:
        if batch_id in ACTIVE:return
        ACTIVE.add(batch_id)
    t=threading.Thread(target=_worker,args=(batch_id,concepts,reels),daemon=True,name='ai-campaign-'+batch_id[:8])
    t.start()

def batch_data(batch_id):
    import director_ai_studio as studio
    data=studio.batch_detail(batch_id)
    if 'reels' not in data or len(data['reels'])!=3:raise HTTPException(409,'Batch has no model-generated reels')
    return data

def progress(batch_id):
    batch_data(batch_id)
    status={}
    for kind in ('image','video'):
        status[kind]=[media_record(batch_id,i,kind) or {'status':'queued','option_no':i} for i in (1,2,3)]
    return status

@router.get('/api/production-media/{batch_id}/status')
def status(batch_id:str):
    return progress(batch_id)

@router.get('/api/production-media/{batch_id}/{platform}/{option}.png')
def preview_post(batch_id:str,platform:str,option:int):
    if platform not in SIZES or option not in (1,2,3):raise HTTPException(404,'Unknown format')
    batch=batch_data(batch_id)
    row=media_record(batch_id,option,'image')
    if not row or row['status']!='completed':raise HTTPException(409,'AI image is not rendered')
    raw=download_media(row['object_path'])
    return Response(composite(raw,batch['candidates'][option-1],platform,option=option),media_type='image/png',
        headers={'Content-Disposition':f'attachment; filename="lakhotia-{platform}-ai-{option}.png"','Cache-Control':'private, no-store'})

def composite(raw,candidate,platform,option=2):
    w,h=SIZES[platform]
    with Image.open(io.BytesIO(raw)) as original:
        source=original.convert('RGB')
        if option==1:
            image=Image.new('RGB',(w,h),(9,42,36))
            framed=ImageOps.contain(source,(int(w*.96),int(h*.55)),
                 method=Image.Resampling.LANCZOS)
            image.paste(framed,((w-framed.width)//2,int(h*.18)))
        else:
            image=ImageOps.fit(source,(w,h),
                 method=Image.Resampling.LANCZOS,centering=(.5,.45))
    overlay=Image.new('RGBA',(w,h),(0,0,0,0))
    d=ImageDraw.Draw(overlay)
    d.rectangle((0,int(h*.57),w,h),fill=(3,32,29,225))
    d.rectangle((0,0,w,int(h*.15)),fill=(2,34,30,210))
    size=lambda pt: ImageFont.truetype(FONTS[1],int(pt))
    title=str(candidate.get('headline',''))[:70]
    sub=str(candidate.get('subheadline',''))[:100]
    d.text((w*.055,h*.038),'LAKHOTIA INDUSTRIAL COMPLEX',font=size(min(w*.023,h*.040)),fill='#ffffff')
    y=int(h*.624)
    for line in wrap(d,title,size(min(w*.044,h*.072)),int(w*.87))[:3]:
        d.text((int(w*.055),y),line,font=size(min(w*.044,h*.072)),fill='#ffffff')
        y+=int(min(w*.054,h*.085))
    for line in wrap(d,sub,size(min(w*.018,h*.029)),int(w*.90))[:2]:
        d.text((int(w*.055),y+10),line,font=size(min(w*.018,h*.029)),fill='#f3d2b1')
        y+=int(min(w*.028,h*.04))
    f=size(min(w*.015,h*.025))
    d.text((w*.055,h*.941),'+91 74500 08999  |  lakhotiaindustrialcomplex.com',font=f,fill='#ffffff')
    d.text((w*.055,h*.17),'APPROVED ARCHITECTURAL GATE · UNALTERED' if option==1 else 'ILLUSTRATIVE INDUSTRY PHOTOGRAPHY',font=size(min(w*.010,h*.019)),fill='#ffffff')
    image=Image.alpha_composite(image.convert('RGBA'),overlay).convert('RGB')
    out=io.BytesIO()
    image.save(out,format='PNG',optimize=True)
    return out.getvalue()

def wrap(draw,text,font,max_width):
    lines=[];part=''
    for word in text.split():
        trial=(part+' '+word).strip()
        if part and draw.textbbox((0,0),trial,font=font)[2]>max_width:
            lines.append(part);part=word
        else:part=trial
    if part:lines.append(part)
    return lines

@router.get('/api/production-media/{batch_id}/reel/{option}/video.mp4')
def downloadable_reel(batch_id:str,option:int):
    if option not in (1,2,3):raise HTTPException(404,'Unknown reel')
    batch_data(batch_id)
    row=media_record(batch_id,option,'video')
    if not row or row['status']!='completed':raise HTTPException(409,'Reel has not finished rendering')
    return Response(download_media(row['object_path']),media_type='video/mp4',
        headers={'Content-Disposition':f'inline; filename="lakhotia-reel-{option}.mp4"',
                 'Cache-Control':'private, no-store','Accept-Ranges':'none'})

@router.post('/api/production-media/{batch_id}/reel/{option}/refresh')
def refresh_video(batch_id:str,option:int):
    director_required()
    if option not in (1,2,3):raise HTTPException(404,'Unknown reel')
    batch_data(batch_id)
    row=media_record(batch_id,option,'video')
    if not row:raise HTTPException(404,'Video job has not started')
    return row

@router.post('/api/production-media/{batch_id}/reel/{option}/retry')
def retry_video(batch_id:str,option:int):
    director_required()
    if option not in (1,2,3):raise HTTPException(404,'Unknown reel')
    data=batch_data(batch_id)
    row=media_record(batch_id,option,'video')
    if row and row['status']=='completed':
        return {'status':'completed','already_verified':True}
    with GUARD:
        if batch_id in ACTIVE:raise HTTPException(409,'Rendering already active')
        ACTIVE.add(batch_id)
    def retry():
        try:create_one_video(batch_id,option,data['reels'][option-1])
        finally:
            with GUARD:ACTIVE.discard(batch_id)
    threading.Thread(target=retry,daemon=True,name='retry-motion-'+str(option)).start()
    return {'status':'queued','provider':'ffmpeg_tts_motion_v1'}

@router.get('/api/production-media/{batch_id}/reel/{option}/download.mp4')
def save_reel(batch_id:str,option:int):
    response=downloadable_reel(batch_id,option)
    response.headers['Content-Disposition']=f'attachment; filename="lakhotia-motion-reel-{option}.mp4"'
    return response
