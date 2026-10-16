"""Reference gallery and limited batch intake; never upgrades images to site plans."""
import hashlib
import io
import uuid
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from PIL import Image
from security_roles import director_required
import reference_grid as grid

router=APIRouter()
MAX_BATCH=8

def intake_batch(files,role,source_identity,note):
    director_required()
    if role not in grid.MUTABLE_ONLY:
        raise HTTPException(409,'Batch import is for supporting references only; architectural masters need exact individual verification')
    if not source_identity.strip() or len(source_identity)>300 or len(note)>500:
        raise HTTPException(422,'Source identity and bounded notes are required')
    if not 1<=len(files)<=MAX_BATCH:
        raise HTTPException(422,'Upload 1–8 supporting images per batch')
    # Validate entire batch before writing any file or database record.
    checked=[]
    for filename,raw in files:
        safe_name=Path(filename).name
        digest=grid.validate_image(raw,safe_name,role)
        with Image.open(io.BytesIO(raw)) as img:
            extension='.png' if img.format=='PNG' else '.jpg'
        checked.append((safe_name,raw,digest,extension))
    grid.STORE.mkdir(parents=True,exist_ok=True)
    prepared=[]
    try:
        with grid.dbconn() as db:
            for filename,raw,digest,extension in checked:
                ident=str(uuid.uuid4());target=grid.STORE/(ident+extension)
                target.write_bytes(raw)
                prepared.append(target)
                db.execute("""INSERT INTO reference_grid(id,created,filename,sha256,role,status,note,source_identity,revision)
                              VALUES(?,?,?,?,?,?,?,?,1)""",
                           (ident,datetime.now(timezone.utc).isoformat(),filename,digest,role,
                            'pending_review',note.strip(),source_identity.strip()))
            db.commit()
    except Exception:
        for target in prepared:target.unlink(missing_ok=True)
        raise
    return {'count':len(checked),'status':'pending_review',
            'message':'Supporting references registered for Director curation. No architectural generation permitted.'}

@router.post('/api/reference-grid/batch')
async def batch_upload(assets:list[UploadFile]=File(...),
                       role:str=Form(...),source_identity:str=Form(...),note:str=Form('')):
    director_required()
    if len(assets)>MAX_BATCH:raise HTTPException(422,'Maximum 8 files per batch')
    rows=[]
    for asset in assets:
        content=await asset.read(grid.MAX_BYTES+1)
        rows.append((asset.filename or 'unnamed',content))
    return intake_batch(rows,role,source_identity,note)

@router.get('/reference-gallery',response_class=HTMLResponse)
def gallery_page():
    director_required()
    assets=grid.list_references()
    sections=[]
    for row in assets:
        ident=escape(row['id'],quote=True)
        name=escape(row['filename'])
        role=escape(row['role'])
        status=escape(row['status'])
        note=escape(row['note'])
        approved=status=='verified'
        review=''
        if row['status']=='pending_review':
            review=f'''<form method="post" action="/api/reference-grid/assets/{ident}/review">
            <label>Review note <input name="note" maxlength="500"></label>
            <button name="decision" value="approved_reference">Approve supporting reference</button>
            <button name="decision" value="rejected">Reject</button></form>'''
        sections.append(f'''<article><img src="/api/reference-grid/assets/{ident}/original" alt="{name}" loading="lazy">
        <div><b>{name}</b><p>{role} · {status}</p><small>{note}</small>
        <p><a href="/api/reference-grid/assets/{ident}/original">Original file</a></p>{review}</div></article>''')
    body=''.join(sections) or '<p>No images registered in the current deployment.</p>'
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><title>Architectural Reference Gallery</title>
<style>body{font:15px system-ui;background:#f3f6f4;color:#123c34;max-width:1150px;margin:32px auto;padding:16px}h1{font-size:30px}
article{display:flex;gap:18px;background:white;border-radius:12px;padding:14px;margin:12px 0}
article img{width:280px;height:190px;object-fit:contain;background:#edf0ee;border-radius:7px}
article>div{flex:1;min-width:0}form{display:grid;gap:12px;padding:16px;background:white;border-radius:12px;margin:18px 0}
input,select{padding:10px;max-width:100%}button{padding:11px;background:#0b4940;color:white;border:0;border-radius:6px;cursor:pointer}
small{color:#536b61}a{color:#155f54}
</style></head><body><a href="/reference-grid">← Reference Grid</a>
<h1>Architectural Reference Gallery</h1>
<p>Gate masters are immutable. Other source images are only supporting references; approval does not authorize changing or inventing project architecture.</p>
<form method="post" action="/api/reference-grid/batch" enctype="multipart/form-data">
<h2>Batch-register supporting references</h2>
<label>Upload up to 8 PNG/JPEG images <input name="assets" type="file" accept="image/png,image/jpeg" multiple required></label>
<label>Role <select name="role"><option value="industrial_unit_reference">External industrial shed / warehouse</option>
<option value="brand_design_reference">Brand design style</option><option value="marketing_reference">Marketing photography / artwork</option></select></label>
<label>Source identity <input name="source_identity" placeholder="Drive URL or asset register ID" required maxlength="300"></label>
<label>Notes <input name="note" maxlength="500" placeholder="Asset provenance / approved intended use"></label>
<button>Register supporting images for review</button></form>
<h2>Reference collection</h2>'''+body+'''<p><small>Prototype: local files and metadata may be lost when Render restarts. This is not durable client storage.</small></p></body></html>''')
