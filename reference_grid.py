"""Evidence-gated architectural asset registry. No generative alteration of physical site.

The user's locked gate master is the only pre-authorized architectural image.
Other artwork may be curated for marketing but cannot become a gate master.
Preview storage is ephemeral; production requires durable object storage.
"""
import hashlib
import io
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image
from security_roles import director_required

router = APIRouter()
ROOT = Path(__file__).resolve().parent
DB = ROOT / 'data' / 'pilot.sqlite3'
STORE = ROOT / 'data' / 'reference_grid'
GATE_SHA = '9ccf79e7f6d7ed22c6f65ed8632d2eb29f6bb6e7056f14f9a3f8d82f905430f5'
GATE_NAME = 'Lakhotia_Approved_Gate_From_Final_Print.png'
MAX_BYTES = 24 * 1024 * 1024
ROLES = ('locked_gate_master','approved_plan','industrial_unit_reference','brand_design_reference','marketing_reference')
MUTABLE_ONLY = {'industrial_unit_reference','brand_design_reference','marketing_reference'}
LOCKED_ONLY = {'locked_gate_master','approved_plan'}

def dbconn():
    DB.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS reference_grid(
            id TEXT PRIMARY KEY, created TEXT NOT NULL, filename TEXT NOT NULL,
            sha256 TEXT NOT NULL, role TEXT NOT NULL, status TEXT NOT NULL,
            note TEXT NOT NULL, source_identity TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1
        )""")
        db.commit()
    return sqlite3.connect(DB)

def validate_image(raw:bytes,filename:str,role:str):
    if role not in ROLES:raise HTTPException(422,'Unknown reference classification')
    if not raw or len(raw)>MAX_BYTES:raise HTTPException(413,'Image must be 1 byte to 24 MB')
    if not filename.lower().endswith(('.png','.jpg','.jpeg')):
        raise HTTPException(415,'Only PNG/JPEG references allowed')
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.format not in ('PNG','JPEG') or img.width<600 or img.height<400 or img.width*img.height>32000000:
                raise HTTPException(422,'Invalid image size or format')
            img.verify()
    except HTTPException:raise
    except (ValueError,OSError,Image.DecompressionBombError) as exc:
        raise HTTPException(422,'Cannot validate reference image') from exc
    digest=hashlib.sha256(raw).hexdigest()
    if role=='locked_gate_master':
        if filename!=GATE_NAME or digest!=GATE_SHA:
            raise HTTPException(409,'Gate master does not match locked source file and SHA-256; cannot substitute')
    return digest

@router.post('/api/reference-grid/assets')
async def upload_reference(asset:UploadFile=File(...),role:str=Form(...),note:str=Form(''),source_identity:str=Form('')):
    director_required()
    filename=Path(asset.filename or '').name
    if len(note)>500 or len(source_identity)>300:
        raise HTTPException(422,'Reference metadata too long')
    if role=='approved_plan':
        raise HTTPException(409,'Site plans require an independently verified plan approval workflow; not enabled')
    raw=await asset.read(MAX_BYTES+1)
    digest=validate_image(raw,filename,role)
    if role=='locked_gate_master':
        source_identity='libfile_919a429faf1081919b91e846f88f6d9d'
    if not source_identity.strip():
        raise HTTPException(422,'Source identity/provenance required')
    ident=str(uuid.uuid4());STORE.mkdir(parents=True,exist_ok=True)
    with Image.open(io.BytesIO(raw)) as img:
        ext='.png' if img.format == 'PNG' else '.jpg'
    path=STORE / (ident+ext)
    path.write_bytes(raw)
    try:
        with dbconn() as db:
            # Gate master MUST remain unique. Re-upload is idempotent.
            if role=='locked_gate_master':
                previous=db.execute("SELECT id FROM reference_grid WHERE role='locked_gate_master' AND status='verified'").fetchone()
                if previous:
                    path.unlink(missing_ok=True)
                    return {'id':previous[0],'status':'verified','sha256':digest,'duplicate':True}
            status='verified' if role=='locked_gate_master' else 'pending_review'
            db.execute('INSERT INTO reference_grid(id,created,filename,sha256,role,status,note,source_identity,revision) VALUES(?,?,?,?,?,?,?,?,1)',
              (ident,datetime.now(timezone.utc).isoformat(),filename,digest,role,status,note.strip(),source_identity.strip()))
            db.commit()
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return {'id':ident,'role':role,'sha256':digest,'status':status,
            'warning':'Architectural geometry is locked; other references need Director review; no image edits permitted'}

@router.get('/api/reference-grid/assets')
def list_references():
    with dbconn() as db:
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute('SELECT * FROM reference_grid ORDER BY created DESC LIMIT 100').fetchall()]

@router.post('/api/reference-grid/assets/{asset_id}/review')
def review_reference(asset_id:str,decision:str=Form(...),note:str=Form('')):
    director_required()
    try:ident=str(uuid.UUID(asset_id))
    except ValueError:raise HTTPException(404,'Unknown reference')
    if decision not in ('approved_reference','rejected'):
        raise HTTPException(422,'Invalid review decision')
    if len(note)>500:raise HTTPException(422,'Review note too long')
    with dbconn() as db:
        row=db.execute('SELECT role,status FROM reference_grid WHERE id=?',(ident,)).fetchone()
        if row is None:raise HTTPException(404,'Reference not found')
        if row[0] not in MUTABLE_ONLY or row[1]!='pending_review':
            raise HTTPException(409,'Locked architectural reference cannot be reclassified through this route')
        db.execute('UPDATE reference_grid SET status=?,note=? WHERE id=?',
                   (decision,note.strip(),ident));db.commit()
    return {'id':ident,'status':decision,'role':row[0],
            'architectural_editing_authorized':False}

@router.get('/api/reference-grid/assets/{asset_id}/original')
def source_original(asset_id:str):
    try:ident=str(uuid.UUID(asset_id))
    except ValueError:raise HTTPException(404,'Unknown reference')
    with dbconn() as db:
        row=db.execute('SELECT sha256,role FROM reference_grid WHERE id=?',(ident,)).fetchone()
    if row is None:raise HTTPException(404,'Reference not found')
    path=next((p for p in (STORE/(ident+'.png'),STORE/(ident+'.jpg')) if p.is_file()),None)
    if path is None:raise HTTPException(410,'Ephemeral original file was lost; re-upload source')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=row[0]:
        raise HTTPException(409,'Source integrity check failed; refuse to display altered image')
    return FileResponse(path,media_type='image/png' if path.suffix=='.png' else 'image/jpeg',
           headers={'Cache-Control':'no-store','X-Matrix360-Reference-Role':row[1],
                    'X-Matrix360-Architectural-Mode':'original-unaltered'})

@router.get('/reference-grid',response_class=HTMLResponse)
def reference_grid_page():
    director_required()
    rows=list_references()
    cells=''.join('<tr><td>'+escape(r['filename'])+'</td><td>'+escape(r['role'])+
                  '</td><td>'+escape(r['status'])+'</td><td><a href="/api/reference-grid/assets/'+escape(r['id'])+'/original">Original</a></td></tr>' for r in rows)
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><title>Matrix360 Reference Grid</title></head><body style="font:16px system-ui;max-width:1000px;margin:40px auto;padding:15px;background:#f6f8f6;color:#143e36">
<h1>Lakhotia Architectural Reference Grid</h1><p><strong>Director-only. Architecture remains immutable.</strong></p>
<p>Only the checksum-matched official gate master is automatically verified. Other assets may be filed for reference but are not permitted to redraw or relocate site architecture. Approved plans require a separate verification procedure.</p>
<form action="/api/reference-grid/assets" method="post" enctype="multipart/form-data" style="display:grid;gap:14px;padding:22px;background:white">
<label>Reference image <input type="file" name="asset" accept="image/png,image/jpeg" required></label>
<label>Classification <select name="role"><option value="locked_gate_master">Locked official gate master (exact source required)</option><option value="industrial_unit_reference">Off-site industrial shed/warehouse reference</option><option value="brand_design_reference">Approved design style reference</option><option value="marketing_reference">General marketing reference</option></select></label>
<label>Source identity / provenance <input name="source_identity" placeholder="File ID / project Drive source / approved brief" style="width:95%"></label>
<label>Review notes <input name="note" maxlength="500" style="width:95%"></label>
<button>Register reference (Director)</button></form>
<h2>Registered source images</h2><table border="1" cellpadding="8" style="border-collapse:collapse;width:100%"><tr><th>Filename</th><th>Role</th><th>Status</th><th>Immutable original</th></tr>'''+cells+'''</table>
<p><small>Upload and status responses use JSON; storage currently ephemeral. No generation endpoint is enabled by this page.</small></p></body></html>''')
