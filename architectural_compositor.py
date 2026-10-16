"""Non-generative marketing proof around a checksum-verified immutable Lakhotia gate.

The gate is inserted proportionally without crop, inpainting, stylistic repainting,
or changes to any structures. Output remains an unapproved illustrative proof.
"""
import hashlib
import io
import sqlite3
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, HTMLResponse
from PIL import Image, ImageDraw
from security_roles import director_required
from creative_renderer_v07 import _f
import reference_grid as grid

router=APIRouter()
ROOT=Path(__file__).resolve().parent
W,H=1080,1350
PANEL=(28,315,1052,913)
NAVY='#142c43'
GREEN='#073e36'
ORANGE='#e96125'

def load_verified_gate(reference_id:str):
    try:rid=str(uuid.UUID(reference_id))
    except ValueError as exc:raise HTTPException(404,'Unknown gate reference') from exc
    with grid.dbconn() as db:
        row=db.execute("SELECT role,status,sha256,filename FROM reference_grid WHERE id=?",(rid,)).fetchone()
    if row is None:raise HTTPException(404,'No gate master registered with this identifier')
    if row[0]!='locked_gate_master' or row[1]!='verified' or row[2]!=grid.GATE_SHA or row[3]!=grid.GATE_NAME:
        raise HTTPException(409,'Reference is not the checksum-verified locked gate master')
    path=grid.STORE/(rid+'.png')
    if not path.is_file():raise HTTPException(410,'Immutable gate original is missing on ephemeral server')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=grid.GATE_SHA:
        raise HTTPException(409,'Architectural original integrity failure')
    return raw

def make_gate_proof(raw:bytes,headline:str='Land at the right place for your business'):
    if len(headline)>90 or not headline.strip():
        raise HTTPException(422,'Invalid headline')
    # Recheck at render boundary. Do not use metadata-only approval.
    if hashlib.sha256(raw).hexdigest()!=grid.GATE_SHA:
        raise HTTPException(409,'Invalid architectural master bytes')
    im=Image.new('RGB',(W,H),'#f9f9f5')
    draw=ImageDraw.Draw(im)
    draw.rectangle((0,0,W,12),fill=ORANGE)
    with Image.open(ROOT/'assets'/'lakhotia_group_logo_official.png') as src:
        logo=src.convert('RGBA');logo.thumbnail((240,76),Image.Resampling.LANCZOS)
        im.paste(logo,(42,34),logo)
    draw.text((43,123),'LAKHOTIA INDUSTRIAL COMPLEX',font=_f(23,True),fill=GREEN)
    # The heading is a separate graphic element; NEVER paint onto the master.
    words=headline.split();lines=[];part=''
    for word in words:
        maybe=(part+' '+word).strip()
        if draw.textbbox((0,0),maybe,font=_f(46,True))[2]>990 and part:
            lines.append(part);part=word
        else:part=maybe
    if part:lines.append(part)
    if len(lines)>2:raise HTTPException(422,'Headline exceeds allocated layout')
    headline_font=_f(46,True)
    last_bottom=0
    for i,line in enumerate(lines):
        top=166+i*54
        bounds=draw.textbbox((43,top),line,font=headline_font)
        last_bottom=max(last_bottom,bounds[3])
    # Fixed spacing is not sufficient for wrapped headlines. Refuse overlaps
    # instead of silently covering characters with the architectural panel.
    if last_bottom+28>PANEL[1]:
        raise HTTPException(422,'Headline exceeds safe image clearance')
    for i,line in enumerate(lines):
        draw.text((43,166+i*54),line,font=headline_font,fill=NAVY)
    # The architectural master is fitted in full, not cropped or redrawn.
    source=Image.open(io.BytesIO(raw)).convert('RGB')
    x0,y0,x1,y1=PANEL
    target_w,target_h=x1-x0,y1-y0
    source.thumbnail((target_w,target_h),Image.Resampling.LANCZOS)
    x=x0+(target_w-source.width)//2
    y=y0+(target_h-source.height)//2
    draw.rectangle((x0-2,y0-2,x1+2,y1+2),fill='#e4e7e4')
    im.paste(source,(x,y))
    draw=ImageDraw.Draw(im)
    draw.rectangle((28,927,1052,1118),fill='#edf1ed')
    stats=(('1,000','bighas under','development'),('2,500+','bighas planned','expansion'),('~4 km','from NH-16','Howrah'))
    for idx,(number,a,b) in enumerate(stats):
        xx=52+idx*338
        draw.text((xx,948),number,font=_f(40,True),fill=NAVY)
        draw.text((xx,1016),a,font=_f(22),fill=GREEN)
        draw.text((xx,1050),b,font=_f(22),fill=GREEN)
        if idx<2:draw.line((xx+303,947,xx+303,1090),fill='#b9cac0',width=2)
    draw.text((43,1140),'Manufacturing  /  Warehousing  /  Logistics',font=_f(26,True),fill=NAVY)
    draw.rectangle((0,1192,W,H),fill=GREEN)
    draw.text((43,1209),'Discuss your industrial land requirement',font=_f(22,True),fill='white')
    draw.text((43,1253),'+91 74500 08999',font=_f(33,True),fill='white')
    draw.text((536,1268),'lakhotiaindustrialcomplex.com',font=_f(21),fill='white')
    draw.text((43,1320),'ARCHITECTURAL VISUAL · INTERNAL PROOF · NO PUBLISHING APPROVAL',font=_f(13),fill='#c9e0d7')
    output=io.BytesIO();im.save(output,format='PNG');return output.getvalue(),(x,y,source.width,source.height)

@router.get('/api/architectural-compositor/gate/{reference_id}/proof')
def locked_gate_proof(reference_id:str):
    director_required()
    raw=load_verified_gate(reference_id)
    result,_=make_gate_proof(raw)
    return Response(result,media_type='image/png',
        headers={'Cache-Control':'no-store','X-Matrix360-Proof':'internal-only',
                 'Content-Disposition':'inline; filename="lakhotia-architectural-master-proof.png"'})

@router.get('/architectural-compositor',response_class=HTMLResponse)
def compositor_page():
    director_required()
    with grid.dbconn() as db:
        rows=db.execute("SELECT id,filename FROM reference_grid WHERE role='locked_gate_master' AND status='verified'").fetchall()
    if not rows:return HTMLResponse('<h1>No verified gate master</h1><p><a href="/reference-grid">Register the checksum-verified master</a> first.</p>')
    from html import escape
    cards=''.join('<section style="background:white;padding:18px;margin:15px 0;border-radius:12px"><h3>'+
        escape(row[1])+'</h3><p>Original image remains unchanged and cannot be redrawn.</p><a href="/api/architectural-compositor/gate/'+escape(row[0])+'/proof">Generate controlled proof PNG</a></section>' for row in rows)
    return HTMLResponse('<html><head><meta charset="utf-8"><title>Master-preserving compositor</title></head><body style="font:16px system-ui;background:#f3f6f3;color:#173e37;max-width:950px;margin:35px auto;padding:12px"><a href="/reference-grid">Reference Grid</a><h1>Architectural master-preserving compositor</h1><p>This compositor adds graphic panels OUTSIDE the unchanged gate artwork. No AI-generated site features, editing or publishing.</p>'+cards+'</body></html>')
