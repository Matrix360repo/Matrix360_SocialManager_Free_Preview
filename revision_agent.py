"""Additive local versioning of creative options; manual text revisions until AI credentials are configured."""
import json, sqlite3, uuid, zipfile, io, shutil
from pathlib import Path
from datetime import datetime, timezone
from html import escape
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, RedirectResponse
from engine import render_card, verify
from visual_layouts_v12 import render as render_visual_v12, MODES
import review_addon as reviews

router=APIRouter()
BASE=Path(__file__).resolve().parent
DB=BASE/'data'/'pilot.sqlite3'
RENDERS=BASE/'data'/'renders'

def stamp(): return datetime.now(timezone.utc).isoformat()
def dbconn():
    db=sqlite3.connect(DB,timeout=15); db.row_factory=sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('''CREATE TABLE IF NOT EXISTS creative_versions (
      draft_id TEXT NOT NULL, option_no INTEGER NOT NULL, version_no INTEGER NOT NULL,
      created_at TEXT NOT NULL, created_by TEXT NOT NULL, feedback TEXT NOT NULL,
      candidate_json TEXT NOT NULL, compliance_json TEXT NOT NULL, image_file TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'review', approved_by TEXT,
      PRIMARY KEY (draft_id,option_no,version_no))''')
    db.commit();return db

def _initial(db,draft_id,opt):
    row=reviews.draft(db,draft_id);reviews.option_check(row,opt)
    existing=db.execute('SELECT 1 FROM creative_versions WHERE draft_id=? AND option_no=? AND version_no=1',(draft_id,opt)).fetchone()
    if existing:return
    candidate=next((c for c in json.loads(row['payload']) if int(c['option'])==opt),None)
    if not candidate:raise HTTPException(404,'Candidate missing')
    check=reviews.option_check(row,opt)
    file=RENDERS/f'{draft_id}_{opt}.png'
    if not file.is_file():raise HTTPException(404,'Original render is missing')
    reviews.ensure_records(db,draft_id)
    old=db.execute('SELECT status, reviewer FROM creative_reviews WHERE draft_id=? AND option_no=?',(draft_id,opt)).fetchone()
    status='approved' if old and old['status']=='approved' else 'review'
    db.execute('INSERT OR IGNORE INTO creative_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)',
               (draft_id,opt,1,stamp(),'initial_import','',json.dumps(candidate,ensure_ascii=False),json.dumps(check),str(file.relative_to(BASE)),status,old['reviewer'] if status=='approved' else None))
    db.commit()

def latest(db,draft_id,opt):
    _initial(db,draft_id,opt)
    return db.execute('SELECT * FROM creative_versions WHERE draft_id=? AND option_no=? ORDER BY version_no DESC LIMIT 1',(draft_id,opt)).fetchone()

def _version(db,draft_id,opt,n):
    _initial(db,draft_id,opt)
    row=db.execute('SELECT * FROM creative_versions WHERE draft_id=? AND option_no=? AND version_no=?',(draft_id,opt,n)).fetchone()
    if not row:raise HTTPException(404,'Version not found')
    return row

def _file(v):
    path=(BASE/v['image_file']).resolve()
    if not path.is_relative_to(RENDERS.resolve()):raise HTTPException(500,'Invalid stored image path')
    if not path.is_file():raise HTTPException(404,'Revision image not found')
    return path

@router.get('/api/revisions/{draft_id}/{opt}')
def states(draft_id:str,opt:int):
    with dbconn() as db:
        latest(db,draft_id,opt)
        rows=db.execute('SELECT version_no,created_at,created_by,feedback,compliance_json,status,approved_by FROM creative_versions WHERE draft_id=? AND option_no=? ORDER BY version_no',(draft_id,opt)).fetchall()
    return {'draft_id':draft_id,'option':opt,'versions':[{'version':r['version_no'],'created_at':r['created_at'],'created_by':r['created_by'],'feedback':r['feedback'],'compliance':json.loads(r['compliance_json']),'status':r['status'],'approved_by':r['approved_by']} for r in rows]}

@router.post('/api/revisions/{draft_id}/{opt}/create')
def create_revision(draft_id:str,opt:int,reviewer:str=Form(...),headline:str=Form(...),subheadline:str=Form(...),caption:str=Form(...),cta:str=Form(...),feedback:str=Form(...),design_style:str=Form('planning_infographic')):
    if opt not in (1,2,3):raise HTTPException(404,'Invalid option')
    if design_style not in MODES:raise HTTPException(422,'Invalid design direction')
    if not 2<=len(reviewer.strip())<=100:raise HTTPException(422,'Reviewer required')
    if not feedback.strip() or len(feedback)>3000:raise HTTPException(422,'Revision feedback required (max 3000 characters)')
    fields={'headline':headline,'subheadline':subheadline,'caption':caption,'cta':cta}
    for name,val in fields.items():
        if not val.strip() or len(val)>({'caption':2500,'subheadline':250,'headline':140,'cta':140}[name]):raise HTTPException(422,f'Invalid {name}')
    with dbconn() as db:
        previous=latest(db,draft_id,opt)
        original=json.loads(previous['candidate_json'])
        candidate={**original,**{k:v.strip() for k,v in fields.items()}}
        candidate['generator']='manual_revision'
        candidate['design_style']=design_style
        checks=verify([candidate]); check=checks[0]
        if not check.get('passed'):
            raise HTTPException(409,'Compliance blocked revision: '+ '; '.join(check.get('issues',[])))
        current=int(previous['version_no']); next_num=current+1
        # Each new revision has an independent, immutable image asset.
        file=RENDERS/f'{draft_id}_{opt}_v{next_num}.png'
        if file.exists():raise HTTPException(409,'Revision file conflict; retry after inspecting stored versions')
        try:
            render_visual_v12(candidate,file,design_style)
            if not file.is_file() or file.stat().st_size==0:raise RuntimeError('Renderer returned no image')
            db.execute('BEGIN IMMEDIATE')
            actual=db.execute('SELECT MAX(version_no) FROM creative_versions WHERE draft_id=? AND option_no=?',(draft_id,opt)).fetchone()[0]
            if actual!=current:raise HTTPException(409,'Another revision was created; reload before retrying')
            db.execute("UPDATE creative_reviews SET status='revision_requested', reviewer=?, updated_at=? WHERE draft_id=? AND option_no=?",(reviewer.strip(),stamp(),draft_id,opt))
            db.execute('INSERT INTO creative_versions VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                       (draft_id,opt,next_num,stamp(),reviewer.strip(),feedback.strip(),json.dumps(candidate,ensure_ascii=False),json.dumps(check),str(file.relative_to(BASE)),'review',None))
            db.commit()
        except Exception:
            db.rollback();file.unlink(missing_ok=True);raise
    return {'draft_id':draft_id,'option':opt,'version':next_num,'status':'review','design_style':design_style,'provider':'manual_revision','compliance':check,'preview_url':f'/api/revisions/{draft_id}/{opt}/preview/{next_num}'}

@router.get('/api/revisions/{draft_id}/{opt}/preview/{n}')
def preview(draft_id:str,opt:int,n:int):
    with dbconn() as db:v=_version(db,draft_id,opt,n);path=_file(v)
    return FileResponse(path,media_type='image/png')

@router.post('/api/revisions/{draft_id}/{opt}/{n}/approve')
def approve(draft_id:str,opt:int,n:int,reviewer:str=Form(...)):
    if len(reviewer.strip())<2:raise HTTPException(422,'Reviewer required')
    with dbconn() as db:
        v=_version(db,draft_id,opt,n)
        if n!=latest(db,draft_id,opt)['version_no']:raise HTTPException(409,'Only the latest version can be approved')
        if not json.loads(v['compliance_json']).get('passed'):raise HTTPException(409,'Compliance blocked approval')
        db.execute("UPDATE creative_versions SET status='superseded' WHERE draft_id=? AND option_no=? AND status='approved'",(draft_id,opt))
        db.execute("UPDATE creative_versions SET status='approved', approved_by=? WHERE draft_id=? AND option_no=? AND version_no=?",(reviewer.strip(),draft_id,opt,n))
        db.execute("UPDATE creative_reviews SET status='approved', reviewer=?, updated_at=? WHERE draft_id=? AND option_no=?",(reviewer.strip(),stamp(),draft_id,opt))
        db.commit()
    return {'option':opt,'approved_version':n,'status':'approved'}

@router.get('/api/revisions/{draft_id}/{opt}/{n}/package')
def package(draft_id:str,opt:int,n:int):
    with dbconn() as db:
        v=_version(db,draft_id,opt,n)
        if v['status']!='approved':raise HTTPException(403,'This version is not approved')
        if latest(db,draft_id,opt)['version_no']!=n:raise HTTPException(403,'A newer revision is awaiting review')
        file=_file(v);content=json.loads(v['candidate_json'])
        manifest={'draft_id':draft_id,'option':opt,'version':n,'approved_by_self_declared_reviewer':v['approved_by'],'content':content,'compliance':json.loads(v['compliance_json']),'no_live_publishing':True}
        buf=io.BytesIO()
        with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
            z.write(file,'creative.png');z.writestr('caption.txt',content.get('caption',''));z.writestr('campaign.json',json.dumps(manifest,indent=2,ensure_ascii=False))
    buf.seek(0)
    return StreamingResponse(buf,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="lakhotia-{draft_id}-option{opt}-v{n}.zip"'})

@router.get('/revisions/{draft_id}/{opt}',response_class=HTMLResponse)
def page(draft_id:str,opt:int):
    with dbconn() as db:
        last=latest(db,draft_id,opt)
        candidate=json.loads(last['candidate_json'])
        versions=db.execute('SELECT version_no,status,feedback,created_by FROM creative_versions WHERE draft_id=? AND option_no=? ORDER BY version_no DESC',(draft_id,opt)).fetchall()
        feedback=db.execute("SELECT feedback FROM creative_events WHERE draft_id=? AND option_no=? AND action='revision_requested' AND trim(feedback)!='' ORDER BY event_id DESC LIMIT 1",(draft_id,opt)).fetchone()
    def textarea(name,value,limit,rows=3):return f'<label>{name.capitalize()}<textarea name="{name}" maxlength="{limit}" rows="{rows}" required>{escape(value)}</textarea></label>'
    rows=''.join(f'<li>Version {v["version_no"]}: {escape(v["status"])} by {escape(v["created_by"])} <a href="/api/revisions/{escape(draft_id)}/{opt}/preview/{v["version_no"]}" target="_blank">View image</a> — {escape(v["feedback"] or "Original")}</li>' for v in versions)
    approve_form=f'''<form action="/revisions/{escape(draft_id)}/{opt}/{last['version_no']}/approve" method="post"><input name="reviewer" placeholder="Reviewer name" required minlength="2"><button>Approve latest version (local test)</button></form>''' if last['status']!='approved' else '<p>Latest version approved.</p>'
    dl=f'<p><a href="/api/revisions/{escape(draft_id)}/{opt}/{last["version_no"]}/package">Download approved ZIP</a></p>' if last['status']=='approved' else '<p>Export locked pending approval.</p>'
    return HTMLResponse(f'''<!doctype html><html><head><meta charset="utf-8"><title>Creative revision</title><style>body{{font:15px system-ui;color:#103e35;background:#f3f6f5;margin:30px auto;max-width:1050px;padding:0 15px}}article{{background:white;padding:20px;border-radius:12px;margin:16px 0}}.split{{display:grid;grid-template-columns:270px 1fr;gap:22px}}img{{width:100%}}label{{display:block;margin:12px 0}}textarea,input,select{{display:block;width:95%;padding:10px}}button{{padding:12px;background:#e9561a;color:white;border:0;border-radius:5px}}li{{padding:7px}}@media(max-width:650px){{.split{{grid-template-columns:1fr}}}}</style></head><body><p><a href="/review-v2/{escape(draft_id)}">← Return to creative review</a></p><h1>Option {opt} — revision workspace</h1><p><a href="/ai-revisions/{escape(draft_id)}/{opt}">Open AI Revision Agent →</a></p><p>Visual redesign is controlled by the selected design direction, not freeform AI interpretation. No publishing is performed.</p><article class="split"><div><img src="/api/revisions/{escape(draft_id)}/{opt}/preview/{last['version_no']}"><p>Latest: v{last['version_no']} ({escape(last['status'])})</p></div><div><h2>Create next version</h2><form method="post" action="/revisions/{escape(draft_id)}/{opt}/create"><input name="reviewer" placeholder="Reviewer name" required minlength="2">{textarea('headline',candidate.get('headline',''),140)}{textarea('subheadline',candidate.get('subheadline',''),250)}{textarea('caption',candidate.get('caption',''),2500,5)}{textarea('cta',candidate.get('cta',''),140)}<label>Visual design direction<select name="design_style" required><option value="editorial_split">Editorial split — image + text panels</option><option value="bold_typography">Bold typography — dark, high contrast</option><option value="planning_infographic">Planning infographic — three-stage diagram</option></select></label>{textarea('feedback',feedback['feedback'] if feedback else 'Explain why this version is needed',3000)}<button>Generate new PNG version</button></form></div></article><article><h2>Latest version approval</h2>{approve_form}{dl}</article><article><h2>Version history</h2><ul>{rows}</ul></article></body></html>''')

@router.post('/revisions/{draft_id}/{opt}/create')
def submit(draft_id:str,opt:int,reviewer:str=Form(...),headline:str=Form(...),subheadline:str=Form(...),caption:str=Form(...),cta:str=Form(...),feedback:str=Form(...),design_style:str=Form('planning_infographic')):
    create_revision(draft_id,opt,reviewer,headline,subheadline,caption,cta,feedback,design_style)
    return RedirectResponse(f'/revisions/{draft_id}/{opt}',status_code=303)

@router.post('/revisions/{draft_id}/{opt}/{n}/approve')
def submit_approval(draft_id:str,opt:int,n:int,reviewer:str=Form(...)):
    approve(draft_id,opt,n,reviewer)
    return RedirectResponse(f'/revisions/{draft_id}/{opt}',status_code=303)
