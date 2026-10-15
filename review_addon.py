"""Local-only per-option review and immutable revision requests for Matrix360 Lakhotia.
No AI revision execution or live publication. Existing drafts schema is untouched.
"""
import io, json, sqlite3, zipfile
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, RedirectResponse

router=APIRouter()
BASE=Path(__file__).resolve().parent
DB=BASE/'data'/'pilot.sqlite3'
RENDERS=BASE/'data'/'renders'

def now():return datetime.now(timezone.utc).isoformat()
def connect():
    db=sqlite3.connect(DB, timeout=15)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA busy_timeout=15000')
    db.execute('''CREATE TABLE IF NOT EXISTS creative_reviews (
      draft_id TEXT NOT NULL, option_no INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'review',
      reviewer TEXT, updated_at TEXT NOT NULL, PRIMARY KEY(draft_id,option_no))''')
    db.execute('''CREATE TABLE IF NOT EXISTS creative_events (
      event_id INTEGER PRIMARY KEY AUTOINCREMENT, draft_id TEXT NOT NULL, option_no INTEGER NOT NULL,
      created_at TEXT NOT NULL, action TEXT NOT NULL, reviewer TEXT NOT NULL, feedback TEXT NOT NULL DEFAULT '',
      version INTEGER NOT NULL)''')
    db.commit()
    return db

def draft(db,draft_id):
    row=db.execute('SELECT id,topic,payload,checks FROM drafts WHERE id=?',(draft_id,)).fetchone()
    if row is None:raise HTTPException(404,'Draft not found')
    return row

def option_check(row,option):
    if option not in (1,2,3):raise HTTPException(404,'Invalid option')
    checks=json.loads(row['checks'])
    return next((x for x in checks if int(x.get('option',-1))==option),{'passed':False,'issues':['Missing compliance review']})

def ensure_records(db,draft_id):
    for opt in (1,2,3):
        db.execute('INSERT OR IGNORE INTO creative_reviews(draft_id,option_no,status,updated_at) VALUES(?,?,?,?)',(draft_id,opt,'review',now()))
    db.commit()

@router.get('/api/review-v2/{draft_id}')
def review_state(draft_id:str):
    with connect() as db:
        row=draft(db,draft_id);ensure_records(db,draft_id)
        states=[dict(x) for x in db.execute('SELECT * FROM creative_reviews WHERE draft_id=? ORDER BY option_no',(draft_id,))]
        events=[dict(x) for x in db.execute('SELECT * FROM creative_events WHERE draft_id=? ORDER BY event_id DESC',(draft_id,))]
    return {'draft_id':draft_id,'topic':row['topic'],'options':states,'events':events,'candidate_versions':'original artwork retained; revisions stored as requests pending execution'}

@router.post('/api/review-v2/{draft_id}/{option}/decision')
def review_decision(draft_id:str,option:int,action:str=Form(...),reviewer:str=Form(...),feedback:str=Form('')):
    if action not in ('approved','rejected','revision_requested'):raise HTTPException(422,'Unknown action')
    if not 2<=len(reviewer.strip())<=100:raise HTTPException(422,'Reviewer must have 2–100 characters')
    if len(feedback)>3000:raise HTTPException(422,'Feedback too long')
    if action=='revision_requested' and not feedback.strip():raise HTTPException(422,'Revision feedback is required')
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        row=draft(db,draft_id);chk=option_check(row,option);ensure_records(db,draft_id)
        if action=='approved' and not chk.get('passed'):
            raise HTTPException(409,'Compliance check failed; cannot approve')
        existing=db.execute('SELECT status FROM creative_reviews WHERE draft_id=? AND option_no=?',(draft_id,option)).fetchone()
        if existing['status']=='approved' and action!='approved':
            raise HTTPException(409,'Approved asset is locked; create a new revision workflow instead')
        prior=db.execute('SELECT action, reviewer, feedback FROM creative_events WHERE draft_id=? AND option_no=? ORDER BY event_id DESC LIMIT 1',(draft_id,option)).fetchone()
        if prior and prior['action']==action and prior['reviewer']==reviewer.strip() and prior['feedback']==feedback.strip():
            db.commit()
            return {'draft_id':draft_id,'option':option,'status':action,'deduplicated':True,'message':'Duplicate review request ignored'}
        count=db.execute('SELECT COALESCE(MAX(version),0) FROM creative_events WHERE draft_id=? AND option_no=?',(draft_id,option)).fetchone()[0]
        new_version=count+1
        db.execute('UPDATE creative_reviews SET status=?, reviewer=?,updated_at=? WHERE draft_id=? AND option_no=?',(action,reviewer.strip(),now(),draft_id,option))
        db.execute('INSERT INTO creative_events(draft_id,option_no,created_at,action,reviewer,feedback,version) VALUES(?,?,?,?,?,?,?)',(draft_id,option,now(),action,reviewer.strip(),feedback.strip(),new_version))
        db.commit()
    return {'draft_id':draft_id,'option':option,'status':action,'event_version':new_version,'execution':'feedback recorded; AI revisions not automatically generated'}

@router.get('/api/review-v2/{draft_id}/{option}/download')
def individual_download(draft_id:str,option:int):
    with connect() as db:
        row=draft(db,draft_id);option_check(row,option);ensure_records(db,draft_id)
        state=db.execute('SELECT status FROM creative_reviews WHERE draft_id=? AND option_no=?',(draft_id,option)).fetchone()
    if state['status']!='approved':raise HTTPException(403,'Individual creative approval required')
    file=RENDERS/f'{draft_id}_{option}.png'
    if not file.is_file():raise HTTPException(404,'Image missing')
    return FileResponse(file,media_type='image/png',filename=f'lakhotia-approved-{draft_id}-option-{option}.png')

@router.get('/api/review-v2/{draft_id}/{option}/package')
def individual_package(draft_id:str,option:int):
    with connect() as db:
        row=draft(db,draft_id);option_check(row,option);ensure_records(db,draft_id)
        state=db.execute('SELECT status,reviewer FROM creative_reviews WHERE draft_id=? AND option_no=?',(draft_id,option)).fetchone()
        events=[dict(x) for x in db.execute('SELECT * FROM creative_events WHERE draft_id=? AND option_no=? ORDER BY event_id',(draft_id,option))]
    if state['status']!='approved':raise HTTPException(403,'Individual creative approval required')
    file=RENDERS/f'{draft_id}_{option}.png'
    if not file.is_file():raise HTTPException(404,'Image missing')
    candidates=json.loads(row['payload'])
    candidate=next((x for x in candidates if int(x.get('option',-1))==option),None)
    if candidate is None:raise HTTPException(404,'Candidate not found')
    manifest={'draft_id':draft_id,'option':option,'topic':row['topic'],'approved_by_self_declared_reviewer':state['reviewer'],'content':candidate,'history':events,'source':'local prototype; independent authentication not yet implemented'}
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
        z.write(file,'creative.png');z.writestr('campaign.json',json.dumps(manifest,ensure_ascii=False,indent=2));z.writestr('caption.txt',candidate.get('caption',''))
    buf.seek(0)
    return StreamingResponse(buf,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="lakhotia-{draft_id}-{option}-approved.zip"'})

@router.get('/review-v2/{draft_id}',response_class=HTMLResponse)
def review_ui(draft_id:str):
    with connect() as db:
        row=draft(db,draft_id);ensure_records(db,draft_id)
        states={x['option_no']:dict(x) for x in db.execute('SELECT * FROM creative_reviews WHERE draft_id=?',(draft_id,))}
        events=[dict(x) for x in db.execute('SELECT * FROM creative_events WHERE draft_id=? ORDER BY event_id DESC',(draft_id,))]
        candidates=json.loads(row['payload'])
    parts=[]
    for c in candidates:
        opt=int(c['option']);st=states[opt];check=option_check(row,opt)
        form='' if st['status']=='approved' else f'''<form method="post" action="/review-v2/{escape(draft_id)}/{opt}/submit">
          <label>Reviewer <input name="reviewer" required minlength="2" maxlength="100" placeholder="Tanmayi"></label>
          <label>Decision <select name="action"><option value="revision_requested">Request revision</option><option value="approved">Approve option</option><option value="rejected">Reject option</option></select></label>
          <label>Feedback <textarea name="feedback" rows="3" maxlength="3000" placeholder="Describe the change requested"></textarea></label><button>Save decision</button></form>'''
        dl=f'<a href="/api/review-v2/{escape(draft_id)}/{opt}/package">Download approved ZIP</a>' if st['status']=='approved' else 'Export locked until option approved'
        dl+=f' · <a href="/revisions/{escape(draft_id)}/{opt}">Open revision workspace</a>'
        parts.append(f'''<article><img src="/api/drafts/{escape(draft_id)}/preview/{opt}" alt="Creative {opt}"><div><h2>Option {opt}: {escape(c.get('headline',''))}</h2>
          <p><b>Status:</b> {escape(st['status'])} · <b>Compliance:</b> {'passed' if check.get('passed') else 'blocked'}</p>
          <p>{escape(c.get('caption',''))}</p>{form}<p>{dl}</p></div></article>''')
    audit=''.join(f'<li>Option {e["option_no"]}: {escape(e["action"])} by {escape(e["reviewer"])} — {escape(e["feedback"] or "no comments")} (event {e["version"]})</li>' for e in events)
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Lakhotia | Creative Review</title><style>
body{font:15px system-ui;background:#f4f6f6;color:#143b35;margin:0}main{max-width:1100px;margin:35px auto;padding:0 20px}article{display:grid;grid-template-columns:260px 1fr;gap:26px;background:white;padding:20px;margin:18px 0;border-radius:12px;box-shadow:0 2px 12px #0001}img{width:100%;border-radius:7px}input,select,textarea{display:block;width:95%;max-width:450px;padding:10px;margin:5px 0 14px}label{display:block}button{background:#e9561a;color:white;border:0;border-radius:5px;padding:12px 18px}li{margin:8px 0}a{color:#126c59}@media(max-width:650px){article{grid-template-columns:1fr}img{max-width:350px}}</style></head><body><main><p><a href="/">← Dashboard</a></p><h1>Review campaign: '''+escape(row['topic'])+'''</h1><p>Approve each option separately, or record revision instructions. Automatic AI revision is not enabled; feedback is preserved for the next agent stage.</p>'''+''.join(parts)+'''<h2>Decision history</h2><ul>'''+audit+'''</ul></main></body></html>''')

@router.post('/review-v2/{draft_id}/{option}/submit')
def review_ui_submit(draft_id:str,option:int,action:str=Form(...),reviewer:str=Form(...),feedback:str=Form('')):
    review_decision(draft_id,option,action,reviewer,feedback)
    return RedirectResponse(f'/review-v2/{draft_id}',status_code=303)
