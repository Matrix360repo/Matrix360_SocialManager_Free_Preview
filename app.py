"""Matrix 360 Lakhotia pilot: draft -> compliance -> human approval -> export.
No automatic social publication, email sending, or ad spend.
"""
import json, os, re, sqlite3, uuid, secrets, base64
from pathlib import Path
from datetime import datetime, timezone
from html import escape
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, FileResponse, Response
from engine import create as content_create, verify as content_verify, render_card

BASE=Path(__file__).parent
PROFILE=json.loads((BASE/'data/brand_profile.json').read_text(encoding='utf-8'))
DB=BASE/'data/pilot.sqlite3'
app=FastAPI(title='Matrix360 Lakhotia Marketing OS Pilot',version='0.8.0')

@app.middleware('http')
async def require_pilot_auth(request: Request, call_next):
    # In local mode (no secret), bind uvicorn to 127.0.0.1 only.
    # If deployed, set a strong MATRIX360_API_KEY and protect all app endpoints.
    if os.getenv('MATRIX360_CLOUD_MODE') == '1' and request.url.path == '/health':
        return await call_next(request)
    key=os.getenv('MATRIX360_API_KEY','').strip()
    if os.getenv('MATRIX360_CLOUD_MODE') == '1' and (len(key) < 32 or key == 'REPLACE_WITH_A_LONG_RANDOM_SECRET'):
        return Response('Server authentication is not configured',status_code=503)
    if key:
        supplied=request.headers.get('X-Matrix360-Key','')
        basic=request.headers.get('Authorization','')
        if basic.startswith('Basic '):
            try:
                decoded=base64.b64decode(basic[6:],validate=True).decode('utf-8')
                supplied=decoded.partition(':')[2]
            except (ValueError,UnicodeDecodeError):
                pass
        if not secrets.compare_digest(supplied,key):
            return Response('Authentication required',status_code=401,headers={'WWW-Authenticate':'Basic realm="Matrix360 Pilot"'})
    return await call_next(request)

@app.get('/health')
def health():
    return {'status':'ok','mode':'local_demo' if not os.getenv('MATRIX360_API_KEY') else 'protected_pilot','generator':'ai_optional','images':'enabled'}

def conn():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    c.execute('CREATE TABLE IF NOT EXISTS drafts (id TEXT PRIMARY KEY, created_at TEXT, topic TEXT, objective TEXT, platform TEXT, status TEXT, payload TEXT, checks TEXT)')
    c.commit()
    return c

def draft_three(topic, objective, platform):
    """Deterministic offline demonstration. Replace with model-backed structured output later."""
    focus=[('Business decision','The right industrial location starts with the right questions.'),
           ('Planning perspective','Build a foundation for your next business move.'),
           ('Consultative approach','Before choosing industrial land, plan the operation.')]
    candidates=[]
    for i,(pillar,headline) in enumerate(focus,1):
        caption=(f'{headline} {topic.strip().rstrip(".")} matters when assessing operational needs, movement, infrastructure and long-term expansion. '
                 'Lakhotia Industrial Complex on Ranihati–Amta Road, Howrah focuses on manufacturing, warehousing and logistics requirements. '
                 'Discuss your plans with the Lakhotia Group team. Call/WhatsApp +91 74500 08999. '
                 'www.lakhotiaindustrialcomplex.com')
        candidates.append({'option':i,'pillar':pillar,'headline':headline,'subheadline':f'{topic.strip()} — a practical business perspective',
                           'caption':caption,'cta':'Discuss your industrial land requirement',
                           'creative_guidance':'4:5 Instagram card, industrial visual, orange emphasis, verified logo/footer only.',
                           'objective':objective,'platform':platform,'generator':'deterministic_demo'})
    return candidates

def compliance(candidates):
    rules=[]
    for c in candidates:
        txt=' '.join(str(v) for v in c.values())
        issues=[]
        if '74500 08999' not in txt: issues.append('Missing canonical phone')
        if 'lakhotiaindustrialcomplex.com' not in txt: issues.append('Missing canonical website')
        if re.search(r'\b(?:800|1,?000)\s*bighas\b',txt,re.I): issues.append('Area figure requires approval')
        if re.search(r'\b(guaranteed returns|100% ROI|operational fuel station)\b',txt,re.I): issues.append('Unsupported claim')
        rules.append({'option':c['option'],'passed':not issues,'issues':issues,'human_approval_required':True})
    return rules

@app.get('/api/brand')
def brand():return PROFILE
@app.get('/api/drafts')
def drafts():
    with conn() as c:
        rows=c.execute('SELECT id, created_at, topic, objective, platform, status, checks FROM drafts ORDER BY created_at DESC').fetchall()
    return [dict(r) for r in rows]
@app.post('/api/generate')
def generate(topic:str=Form(...),objective:str=Form('Awareness'),platform:str=Form('Instagram')):
    if not topic.strip() or len(topic)>250: raise HTTPException(422,'Topic must be 1–250 characters')
    if platform not in ('Instagram','LinkedIn'):raise HTTPException(422,'Unsupported platform')
    try:
        content, provider=content_create(PROFILE,topic,objective,platform,draft_three)
    except RuntimeError as e:raise HTTPException(502,str(e))
    checks=content_verify(content)
    if len(content)!=3 or len(checks)!=3:
        raise HTTPException(502,'Expected exactly three validated candidates')
    draft_id=str(uuid.uuid4())
    # Generate all image assets before adding a reviewable draft to the database.
    # On failure, clear partial files and leave no broken review-queue entry.
    paths=[BASE/'data'/'renders'/f'{draft_id}_{i}.png' for i in (1,2,3)]
    try:
        for index,candidate in enumerate(content):
            render_card(candidate,paths[index],index)
    except Exception as exc:
        for path in paths:
            path.unlink(missing_ok=True)
        raise HTTPException(500,'Creative rendering failed: '+str(exc)) from exc
    try:
        with conn() as c:
            c.execute('INSERT INTO drafts VALUES (?,?,?,?,?,?,?,?)',(draft_id,datetime.now(timezone.utc).isoformat(),topic,objective,platform,'review',json.dumps(content,ensure_ascii=False),json.dumps(checks)))
            c.commit()
    except Exception:
        for path in paths:path.unlink(missing_ok=True)
        raise
    return {'id':draft_id,'status':'review','provider':provider,'candidates':content,'compliance':checks,'preview_urls':[f'/api/drafts/{draft_id}/preview/{i}' for i in (1,2,3)]}
@app.get('/api/drafts/{draft_id}')
def get_draft(draft_id:str):
    with conn() as c:r=c.execute('SELECT * FROM drafts WHERE id=?',(draft_id,)).fetchone()
    if not r:raise HTTPException(404,'Draft not found')
    d=dict(r);d['payload']=json.loads(d['payload']);d['checks']=json.loads(d['checks']);return d
@app.post('/api/drafts/{draft_id}/decision')
def decision(draft_id:str,action:str=Form(...),reviewer:str=Form(...)):
    if action not in ('approved','rejected','revision_requested'):raise HTTPException(422,'Invalid decision')
    if len(reviewer.strip())<2:raise HTTPException(422,'Reviewer required')
    with conn() as c:
        r=c.execute('SELECT id,checks,status FROM drafts WHERE id=?',(draft_id,)).fetchone()
        if not r:raise HTTPException(404,'Draft not found')
        if r['status']!='review':raise HTTPException(409,'Only drafts under review can be decided')
        if action=='approved' and any(not x['passed'] for x in json.loads(r['checks'])):
            raise HTTPException(409,'Compliance failure. Fix before approval')
        c.execute('UPDATE drafts SET status=? WHERE id=?',(action,draft_id));c.commit()
    return {'id':draft_id,'status':action,'reviewer':reviewer,'note':'Reviewer identity is self-declared in this local prototype; authenticate users in production.'}
@app.get('/api/drafts/{draft_id}/preview/{option}')
def preview(draft_id:str,option:int):
    if option not in (1,2,3):raise HTTPException(404,'Invalid option')
    get_draft(draft_id)
    path=BASE/'data'/'renders'/f'{draft_id}_{option}.png'
    if not path.exists():raise HTTPException(404,'Preview missing')
    return FileResponse(path,media_type='image/png')

@app.get('/api/drafts/{draft_id}/download/{option}')
def download(draft_id:str,option:int):
    data=get_draft(draft_id)
    if data['status']!='approved':raise HTTPException(403,'Human approval required before download')
    if option not in (1,2,3):raise HTTPException(404,'Invalid option')
    file=BASE/'data'/'renders'/f'{draft_id}_{option}.png'
    if not file.exists():raise HTTPException(404,'Rendered image not found')
    return FileResponse(file,media_type='image/png',filename=f'lakhotia-{draft_id}-option-{option}.png')

@app.get('/api/drafts/{draft_id}/export')
def export(draft_id:str):
    data=get_draft(draft_id)
    if data['status']!='approved':raise HTTPException(403,'Only approved drafts may be exported')
    return JSONResponse({'client_id':PROFILE['client_id'],'draft':data},headers={'Content-Disposition':f'attachment; filename="lakhotia-{draft_id}.json"'})
@app.get('/',response_class=HTMLResponse)
def dashboard():
    with conn() as c:
        counts={r['status']:r['n'] for r in c.execute('SELECT status, count(*) n FROM drafts GROUP BY status')}
        recent=c.execute('SELECT id,topic,status,created_at FROM drafts ORDER BY created_at DESC LIMIT 12').fetchall()
    rows=''.join(f'<tr><td>{escape(r["topic"])}</td><td>{escape(r["status"])}</td><td><a href="/draft/{r["id"]}">Review</a></td></tr>' for r in recent)
    return f'''<!doctype html><html><head><meta charset="utf-8"><title>Matrix 360 | Lakhotia</title><style>
    body{{font:15px system-ui;background:#f1f4f5;color:#14342f;margin:0}}main{{max-width:980px;margin:38px auto;padding:0 24px}}header{{background:#073d34;color:white;padding:25px}}h1{{margin:0}}.card{{background:white;border-radius:12px;padding:23px;margin:16px 0;box-shadow:0 2px 10px #0001}}label{{display:block;margin:12px 0}}input,select{{padding:10px;border:1px solid #b8c9c5;border-radius:6px;min-width:280px}}button{{background:#e9561a;color:white;border:0;padding:12px 20px;border-radius:6px;cursor:pointer}}table{{width:100%;border-collapse:collapse}}td,th{{text-align:left;padding:10px;border-bottom:1px solid #ddd}}small{{color:#64756e}}.stat{{display:inline-block;margin-right:25px;font-weight:700}}
    </style></head><body><header><h1>Matrix 360 | Lakhotia Marketing OS</h1><div>Client 001 · Draft → Check → Human Approval → Export</div></header><main><div class="card"><h2>Operator dashboard</h2><div class="stat">Under review: {counts.get('review',0)}</div><div class="stat">Approved: {counts.get('approved',0)}</div><div class="stat">Rejected: {counts.get('rejected',0)}</div><p><small>Offline proof mode; optional model-backed generation when OPENAI_API_KEY is set. No live publishing or ad spend.</small></p></div>
    <div class="card"><h2>Create campaign draft</h2><form action="/api/generate" method="post"><label>Topic<br><input name="topic" required maxlength="250" placeholder="Planning a warehouse expansion"></label><label>Objective<br><select name="objective"><option>Awareness</option><option>Consultation enquiries</option><option>Thought leadership</option></select></label><label>Channel<br><select name="platform"><option>Instagram</option><option>LinkedIn</option></select></label><button type="submit">Generate 3 structured concepts</button></form></div>
    <div class="card"><h2>Review queue</h2><table><tr><th>Topic</th><th>Status</th><th>Action</th></tr>{rows}</table></div><p><small>Approved current development: 1,000 bighas. Group logo integrated; editable layout masters and Industrial Complex lockup still required for production-quality rendering. Generated PNGs are design proofs.</small></p></main></body></html>'''
@app.get('/draft/{draft_id}',response_class=HTMLResponse)
def review_page(draft_id:str):
    d=get_draft(draft_id)
    cards=''.join('<article style="border:1px solid #ccc;padding:12px;margin:12px 0;border-radius:6px"><b>Option '+str(c['option'])+' — '+escape(c['pillar'])+'</b><h3>'+escape(c['headline'])+'</h3><img width="230" src="/api/drafts/'+draft_id+'/preview/'+str(c['option'])+'"><p>'+escape(c['caption'])+'</p><p><a href="/api/drafts/'+draft_id+'/download/'+str(c['option'])+'">Download (after approval)</a></p></article>' for c in d['payload'])
    forms=''
    if d['status']=='review':
        forms=f'<form method="post" action="/api/drafts/{draft_id}/decision"><input name="reviewer" placeholder="Reviewer name" required><select name="action"><option value="approved">Approve</option><option value="revision_requested">Request revision</option><option value="rejected">Reject</option></select><button>Submit review</button></form>'
    return f'<html><head><meta charset="utf-8"></head><body style="max-width:850px;margin:30px auto;font:16px system-ui"><a href="/">← Dashboard</a><h1>{escape(d["topic"])}</h1><p>Status: {escape(d["status"])}</p>{cards}{forms}<p><a href="/api/drafts/{draft_id}/export">Export approved JSON</a></p></body></html>'

from review_addon import router as review_router
app.include_router(review_router)

# Matrix360 local creative revision versioning v1.1
from revision_agent import router as revision_router
app.include_router(revision_router)

from ai_revision_v13 import router as ai_revision_router
app.include_router(ai_revision_router)
