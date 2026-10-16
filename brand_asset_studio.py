"""Lakhotia brand asset staging and proof-only reference composition.

Human review is required because image raster analysis does not reliably detect
legacy text/claims. Public free-preview storage is EPHEMERAL, not client storage.
"""
import hashlib
import io
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from html import escape
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response
from PIL import Image, ImageOps, ImageDraw
from security_roles import director_required
from creative_renderer_v07 import _f

router=APIRouter()
ROOT=Path(__file__).resolve().parent
DIR=ROOT/'data'/'brand_staging'
DB=ROOT/'data'/'pilot.sqlite3'
MAX_BYTES=12*1024*1024
MAX_PIXELS=24000000
ALLOWED_TYPES={'image/jpeg','image/png'}

def dbconn():
    with sqlite3.connect(DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS brand_assets(
          id TEXT PRIMARY KEY, created TEXT NOT NULL, sha256 TEXT NOT NULL,
          filename TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
          status TEXT NOT NULL, review_note TEXT NOT NULL DEFAULT '')""")
        db.commit()
    return sqlite3.connect(DB)

def clean_plate_image(data,content_type):
    if content_type not in ALLOWED_TYPES:raise HTTPException(415,'Only PNG and JPEG allowed')
    if not data or len(data)>MAX_BYTES:raise HTTPException(413,'Image must be 1 byte to 12 MB')
    try:
        with Image.open(io.BytesIO(data)) as src:
            if src.format not in ('PNG','JPEG'):raise HTTPException(415,'Not a PNG/JPEG file')
            w,h=src.size
            if w<900 or h<600 or w*h>MAX_PIXELS:
                raise HTTPException(422,'Image must be at least 900×600 and no more than 24 megapixels')
            img=ImageOps.exif_transpose(src).convert('RGB')
            img.thumbnail((3200,3200),Image.Resampling.LANCZOS)
            output=io.BytesIO();img.save(output,'PNG',optimize=True)
            return output.getvalue(), img.size
    except HTTPException:raise
    except (OSError,ValueError,Image.DecompressionBombError) as exc:
        raise HTTPException(422,'Unsupported or corrupted image') from exc

@router.post('/api/brand-studio/assets')
async def stage_asset(asset: UploadFile=File(...)):
    # Authenticated operator may upload only, never mark artwork as verified.
    data=await asset.read(MAX_BYTES+1)
    normalized,(w,h)=clean_plate_image(data,asset.content_type)
    asset_id=str(uuid.uuid4());DIR.mkdir(parents=True,exist_ok=True)
    (DIR/f'{asset_id}.png').write_bytes(normalized)
    stamp=datetime.now(timezone.utc).isoformat()
    with dbconn() as db:
        db.execute('INSERT INTO brand_assets VALUES(?,?,?,?,?,?,?,?)',
                   (asset_id,stamp,hashlib.sha256(normalized).hexdigest(),
                    Path(asset.filename or 'unnamed').name[:120],w,h,'pending',''))
        db.commit()
    return {'id':asset_id,'status':'pending','image_size':[w,h],
            'warning':'Pending Director confirmation; cannot render until approved'}

@router.get('/api/brand-studio/assets')
def list_assets():
    with dbconn() as db:
        db.row_factory=sqlite3.Row
        rows=db.execute('SELECT id,created,filename,width,height,status,review_note FROM brand_assets ORDER BY created DESC LIMIT 50').fetchall()
    return [dict(row) for row in rows]

@router.get('/api/brand-studio/assets/{asset_id}/image')
def asset_image(asset_id:str):
    try:asset_id=str(uuid.UUID(asset_id))
    except ValueError:raise HTTPException(404,'Unknown asset')
    with dbconn() as db:
        row=db.execute('SELECT id FROM brand_assets WHERE id=?',(asset_id,)).fetchone()
    if not row:raise HTTPException(404,'Unknown asset')
    path=DIR/f'{asset_id}.png'
    if not path.exists():raise HTTPException(410,'Ephemeral image file is missing; re-upload')
    return FileResponse(path,media_type='image/png')

@router.post('/api/brand-studio/assets/{asset_id}/review')
def review_asset(asset_id:str,decision:str=Form(...),attestation:str=Form(''),note:str=Form('')):
    director_required()
    if decision not in ('approved_proof','rejected'):raise HTTPException(422,'Invalid decision')
    if decision=='approved_proof' and attestation!='clean_plate':
        raise HTTPException(422,'Director must confirm no embedded legacy captions, numbers, logos or CTAs')
    try:asset_id=str(uuid.UUID(asset_id))
    except ValueError:raise HTTPException(404,'Unknown asset')
    if len(note)>500:raise HTTPException(422,'Review note too long')
    with dbconn() as db:
        cur=db.execute("UPDATE brand_assets SET status=?, review_note=? WHERE id=? AND status='pending'",
                       (decision,note.strip(),asset_id))
        if cur.rowcount!=1:raise HTTPException(409,'Only existing pending assets can be reviewed')
        db.commit()
    return {'id':asset_id,'status':decision,'reviewer_role':'Director','production_approved':False}

def render_composition(hero,headline='Land at the right place for your business'):
    if len(headline)>90 or not headline.strip():raise HTTPException(422,'Invalid headline')
    green='#063d34';orange='#e95b20';navy='#102a48'
    im=Image.new('RGB',(1080,1350),'#fbfaf7')
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,12),fill=orange)
    # Exact supplied group logo; no generated wordmark.
    with Image.open(ROOT/'assets'/'lakhotia_group_logo_official.png') as src:
        logo=src.convert('RGBA');logo.thumbnail((300,90),Image.Resampling.LANCZOS)
        im.paste(logo,(55,34),logo)
    d.text((61,155),'LAKHOTIA INDUSTRIAL COMPLEX',font=_f(23,True),fill=green)
    # Dynamic headline wrapping, no overflow silently truncated.
    words=headline.split();lines=[];current=''
    for word in words:
        probe=(current+' '+word).strip()
        if d.textbbox((0,0),probe,font=_f(54,True))[2]>970 and current:
            lines.append(current);current=word
        else:current=probe
    if current:lines.append(current)
    if len(lines)>3:raise HTTPException(422,'Headline exceeds composition capacity')
    for i,line in enumerate(lines):d.text((61,218+i*64),line,font=_f(54,True),fill=navy)
    # Hero starts below text hierarchy; do not place previously composed campaign art.
    hero=ImageOps.fit(hero.convert('RGB'),(1080,490),method=Image.Resampling.LANCZOS,centering=(.5,.55))
    im.paste(hero,(0,430));d=ImageDraw.Draw(im)
    d.rectangle((0,919,1080,1098),fill='#f5f5f0')
    stats=[('1,000','bighas under','development'),('2,500+','bighas planned','expansion'),('~4 km','from NH-16','Howrah')]
    for index,(num,a,b) in enumerate(stats):
        x=66+index*355
        d.text((x,947),num,font=_f(43,True),fill=navy)
        d.text((x,1011),a,font=_f(21),fill=green)
        d.text((x,1044),b,font=_f(21),fill=green)
        if index<2:d.line((x+315,951,x+315,1070),fill='#c3d0cb',width=2)
    d.text((60,1125),'Manufacturing  /  Warehousing  /  Logistics',font=_f(24,True),fill=navy)
    d.rectangle((0,1185,1080,1350),fill=green)
    d.text((60,1203),'Discuss your industrial land requirement',font=_f(22,True),fill='white')
    d.text((60,1258),'+91 74500 08999',font=_f(34,True),fill='white')
    d.text((540,1271),'lakhotiaindustrialcomplex.com',font=_f(22),fill='white')
    d.text((58,1324),'INTERNAL PROOF • COMPOSITE IMAGE, NOT VERIFIED SITE PHOTOGRAPHY',font=_f(13),fill='#c1d8cd')
    out=io.BytesIO();im.save(out,'PNG');return out.getvalue()

@router.get('/api/brand-studio/assets/{asset_id}/proof')
def asset_proof(asset_id:str):
    try:asset_id=str(uuid.UUID(asset_id))
    except ValueError:raise HTTPException(404,'Unknown asset')
    with dbconn() as db:
        row=db.execute('SELECT status FROM brand_assets WHERE id=?',(asset_id,)).fetchone()
    if not row:raise HTTPException(404,'Unknown asset')
    if row[0]!='approved_proof':raise HTTPException(403,'Only Director-confirmed clean plates can be used in proof')
    path=DIR/f'{asset_id}.png'
    if not path.exists():raise HTTPException(410,'Ephemeral image missing')
    with Image.open(path) as source:
        result=render_composition(source)
    return Response(result,media_type='image/png',
                    headers={'Cache-Control':'no-store','Content-Disposition':'inline; filename="lakhotia-brand-proof.png"'})

@router.get('/api/brand-studio/assets/{asset_id}/draft/{draft_id}/option/{option}/proof')
def candidate_brand_proof(asset_id:str,draft_id:str,option:int):
    """Preview-only composition of reviewed clean plate with an existing draft.

    No mutation of draft PNGs, review statuses, approvals or export packages.
    This route is not a publication or approval mechanism.
    """
    if option not in (1,2,3):
        raise HTTPException(404,'Unknown candidate option')
    try: asset_id=str(uuid.UUID(asset_id));draft_id=str(uuid.UUID(draft_id))
    except ValueError:raise HTTPException(404,'Unknown asset or draft')
    with dbconn() as db:
        asset_row=db.execute('SELECT status FROM brand_assets WHERE id=?',(asset_id,)).fetchone()
        draft_row=db.execute('SELECT payload,checks,status FROM drafts WHERE id=?',(draft_id,)).fetchone()
    if asset_row is None or draft_row is None:
        raise HTTPException(404,'Asset or draft not found')
    if asset_row[0]!='approved_proof':
        raise HTTPException(403,'Director confirmation required before composing proof')
    if draft_row[2] not in ('review','revision_requested'):
        raise HTTPException(409,'Proof is available for drafts awaiting review only')
    candidates=json.loads(draft_row[0]);checks=json.loads(draft_row[1])
    if len(candidates)!=3 or len(checks)!=3:
        raise HTTPException(409,'Draft lacks complete candidate compliance records')
    candidate=next((c for c in candidates if c.get('option')==option),None)
    check=next((c for c in checks if c.get('option')==option),None)
    if not candidate or not check or not check.get('passed'):
        raise HTTPException(409,'Candidate must pass baseline compliance checks')
    # Re-evaluate with the current engine to avoid accepting previously
    # unqualified project claims from stored draft records.
    from engine import verify
    latest=verify([candidate])
    if not latest[0]['passed']:
        raise HTTPException(409,'Candidate fails current compliance: '+ '; '.join(latest[0]['issues']))
    source=DIR/f'{asset_id}.png'
    if not source.is_file():
        raise HTTPException(410,'Ephemeral source file missing')
    with Image.open(source) as clean:
        result=render_composition(clean,candidate['headline'])
    return Response(result,media_type='image/png',
        headers={'Cache-Control':'no-store',
                 'X-Matrix360-Asset-Status':'internal-proof-only'})

@router.get('/brand-studio',response_class=HTMLResponse)
def brand_studio():
    cards=[]
    for row in list_assets():
        ident=escape(row['id'])
        status=escape(row['status'])
        name=escape(row['filename'])
        if status=='pending':
            action=(f'<form method="post" action="/api/brand-studio/assets/{ident}/review">'
                    '<label><input type="checkbox" name="attestation" value="clean_plate" required> '
                    'I have visually checked this background has no pre-existing text, stale data, old CTA or logos, '
                    'and is cleared for internal composition tests.</label>'
                    '<label>Review note <input name="note" maxlength="500" placeholder="Approved source / usage context"></label>'
                    '<button name="decision" value="approved_proof">Director: approve internal proof</button> '
                    '<button name="decision" value="rejected" formnovalidate>Reject asset</button></form>')
        elif status=='approved_proof':
            action=f'<a href="/api/brand-studio/assets/{ident}/proof">Render proof PNG</a>'
        else:action='Rejected'
        cards.append(f'<li><b>{name}</b> ({status}) — <a href="/api/brand-studio/assets/{ident}/image">View</a> · {action}</li>')
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><title>Matrix360 · Brand Asset Studio</title><style>body{font:16px system-ui;margin:35px auto;max-width:940px;background:#f5f7f4;color:#063d34;padding:15px}article{background:white;padding:26px;border-radius:12px;margin:18px 0}label{display:block;margin:12px 0}input,button{padding:12px}button{background:#e95b20;color:white;border:0;border-radius:6px}li{margin:12px}</style></head><body><p><a href="/campaign-studio">← Campaign Studio</a></p><h1>Reference Asset Studio · Internal Proof Only</h1><article><h2>Stage a clean photographic/industrial background</h2><p>Upload only a licensed, brand-approved, clean background with no embedded old numbers, text, logos or CTAs. Render Free loses uploads on restart.</p><form action="/api/brand-studio/assets" method="post" enctype="multipart/form-data"><label>Clean plate (PNG or JPEG, max 12 MB) <input type="file" name="asset" accept="image/png,image/jpeg" required></label><button>Upload for Director review</button></form><p>Uploads return JSON. Share the returned asset ID with the Director for a review request.</p></article><article><h2>Staged assets</h2><ul>'''+''.join(cards)+'''</ul><p>Director credentials are required to approve a staged background. Approved here means internal proof only—not production or publishing approval.</p></article></body></html>''')
