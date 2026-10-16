"""Unified Director-facing Lakhotia October 16 acceptance demonstration.

Immutable gate source; three styled campaign previews; 30s storyboard;
tracked consultation redirect; role-bound approval and fail-closed publishing.
Demo reviews/click metrics are ephemeral on Render Free, not production records.
"""
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from html import escape
from urllib.parse import quote
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, Response, RedirectResponse
from security_roles import current_actor, director_required
import reference_grid as grid
import reference_persistence as persistence
from campaign_studio_poc import storyboard, CAMPAIGN_ID, metrics

router=APIRouter()
CONCEPTS=(
    dict(id=1,slug='industrial-foundations',eyebrow='THE NEXT INDUSTRIAL CHAPTER',
         title='Land at the right place for your business.',
         desc='Planned for manufacturing, warehousing and logistics.',
         tag='Industrial land · Howrah',style='emerald',facts='1,000 bighas under development'),
    dict(id=2,slug='connected-for-business',eyebrow='LOCATION & CONNECTIVITY',
         title='Your next move starts with location.',
         desc='Ranihati–Amta Road, Howrah. Approx. 4 km from NH-16.',
         tag='Connectivity · West Bengal',style='midnight',facts='Approx. 4 km from NH-16'),
    dict(id=3,slug='consultation-first',eyebrow='EXPANSION PLANNING',
         title='Plan your next industrial chapter.',
         desc='Free consulting by our expert panel. Plot sizes subject to requirement and availability.',
         tag='Consultation · Planning',style='terracotta',facts='2,500+ bighas planned expansion'),
)
PHONE='+91 74500 08999'
WEBSITE='lakhotiaindustrialcomplex.com'

def verified_master():
    """Never replace missing site architecture with a generated approximation."""
    if not grid.restore_gate_record():
        raise HTTPException(503,'Verified architectural master unavailable; no substitute allowed')
    with grid.dbconn() as db:
        record=db.execute("SELECT id FROM reference_grid WHERE role='locked_gate_master' AND status='verified' AND sha256=?",(grid.GATE_SHA,)).fetchone()
    if record is None:
        raise HTTPException(503,'No checksum-verified architectural reference')
    source=grid.STORE/(record[0]+'.png')
    if not source.is_file():
        raise HTTPException(503,'Locked architectural source unavailable')
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=grid.GATE_SHA:
        raise HTTPException(409,'Locked architectural image integrity failure')
    return raw

@router.get('/api/director-demo/gate')
def architectural_image():
    return Response(verified_master(),media_type='image/png',headers={
        'Cache-Control':'private, max-age=120','X-Architectural-Master-SHA256':grid.GATE_SHA,
        'X-Matrix360-Architectural-Mode':'immutable-original'})

def dbconn():
    grid.DB.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(grid.DB,timeout=10)
    db.execute("""CREATE TABLE IF NOT EXISTS director_demo_reviews(
        concept_id INTEGER PRIMARY KEY, status TEXT NOT NULL DEFAULT 'pending',
        reviewer TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
        updated_utc TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS director_demo_audit(
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        concept_id INTEGER NOT NULL, decision TEXT NOT NULL,
        reviewer TEXT NOT NULL, note TEXT NOT NULL, created_utc TEXT NOT NULL)""")
    db.commit()
    return db

def review_states():
    with dbconn() as db:
        rows=db.execute("SELECT concept_id,status,note,updated_utc FROM director_demo_reviews").fetchall()
    return {str(r[0]):{'status':r[1],'note':r[2],'updated_utc':r[3]} for r in rows}

@router.get('/api/director-demo/status')
def demo_status():
    verified_master()
    return {'architectural_master':'sha256_verified','concepts':3,'reviews':review_states(),
            'publishing':'disabled','published_items':0,
            'cta_metrics':metrics(),'disclaimer':'Review data and click counts are disposable on Render Free; tracked clicks are not qualified leads.'}

@router.post('/api/director-demo/concepts/{concept_id}/review')
def review_concept(concept_id:int,decision:str=Form(...),note:str=Form('')):
    director_required()
    if concept_id not in (1,2,3): raise HTTPException(404,'Unknown concept')
    if decision not in ('approved','rejected','revision_requested'): raise HTTPException(422,'Unsupported decision')
    if len(note)>500:raise HTTPException(422,'Review note must be at most 500 characters')
    if decision=='revision_requested' and not note.strip():
        raise HTTPException(422,'A revision request requires a note')
    verified_master()
    now=datetime.now(timezone.utc).isoformat()
    with dbconn() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("""INSERT INTO director_demo_reviews(concept_id,status,reviewer,note,updated_utc)
                      VALUES(?,?,?,?,?) ON CONFLICT(concept_id) DO UPDATE SET
                      status=excluded.status,reviewer=excluded.reviewer,
                      note=excluded.note,updated_utc=excluded.updated_utc""",
                   (concept_id,decision,'Director',note.strip(),now))
        db.execute("""INSERT INTO director_demo_audit(concept_id,decision,reviewer,note,created_utc)
                      VALUES(?,?,?,?,?)""",(concept_id,decision,'Director',note.strip(),now))
        db.commit()
    return {'concept_id':concept_id,'status':decision,'reviewed_by':'Director',
            'publication_authorized':False,'note':'Review decision recorded in preview database; no content sent.'}

@router.post('/api/director-demo/publish')
def publish_blocked():
    director_required()
    raise HTTPException(409,'Publishing integration disabled in controlled pilot. Director approval does not authorize auto-publishing.')

@router.get('/api/director-demo/storyboard')
def director_storyboard():
    return storyboard('Industrial expansion planning','Instagram','Consultation enquiries')

def concept_html(c):
    n=c['id']
    return f'''<article class="concept-wrap" data-concept="{n}">
      <div class="art art-{c['style']}">
        <div class="art-top"><span class="wordmark"><b>LAKHOTIA</b><small>INDUSTRIAL COMPLEX</small></span>
          <span class="edition">MATRIX 360 / 0{n}</span></div>
        <div class="art-copy"><span class="art-eyebrow">{escape(c['eyebrow'])}</span>
           <h3>{escape(c['title'])}</h3><p>{escape(c['desc'])}</p></div>
        <div class="gate-frame"><img src="/api/director-demo/gate" loading="lazy"
             alt="Checksum-verified official Lakhotia gate master, shown without architecture editing">
             <span class="gate-caption">APPROVED ARCHITECTURAL VISUAL · UNALTERED SOURCE</span></div>
        <div class="art-bottom"><span>{escape(c['facts'])}</span><span class="art-arrow">↗</span></div>
        <div class="art-contact">{PHONE} <span>lakhotiaindustrialcomplex.com</span></div>
      </div>
      <div class="concept-meta"><div><span class="concept-number">CONCEPT 0{n}</span>
        <h4>{escape(c['tag'])}</h4></div><span class="status" id="status-{n}">Awaiting review</span></div>
      <p class="micro">Master locked · Original geometry preserved · No invented site structures</p>
      <div class="review-controls">
        <button type="button" class="approve" onclick="review({n},'approved')">Approve</button>
        <button type="button" class="reject" onclick="review({n},'rejected')">Reject</button>
        <button type="button" class="revision" onclick="review({n},'revision_requested')">Request revision</button>
      </div>
    </article>'''

CSS=r"""
:root{--ink:#152e2b;--muted:#72807b;--paper:#f4f5f1;--dark:#102c29;--line:#dce2dc;--orange:#ea6937}
*{box-sizing:border-box}body{margin:0;background:var(--paper);font:15px/1.55 'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;color:var(--ink)}
a{color:inherit}button{font:inherit;cursor:pointer}aside{position:fixed;inset:0 auto 0 0;width:245px;background:#102a28;color:#d9e3db;padding:27px 18px;display:flex;flex-direction:column;z-index:4}
.brand{font-size:23px;font-weight:850;letter-spacing:-1px;color:#fff;padding:0 13px}.brand small{display:block;font-size:10px;letter-spacing:2.6px;color:#94b5a8}
nav{display:grid;gap:7px;margin-top:54px}nav a{color:#b1c8bf;text-decoration:none;padding:13px 15px;border-radius:9px;font-size:13px}
nav a.active,nav a:hover{background:#214b42;color:white}.nav-bottom{margin-top:auto;padding:18px 13px;border-top:1px solid #315149;font-size:11px;color:#b5ccc0}
main{margin-left:245px;padding:0 36px 80px;max-width:1840px}.topbar{display:flex;align-items:center;justify-content:space-between;padding:22px 0;border-bottom:1px solid var(--line);gap:12px}
.crumb{font-size:12px;letter-spacing:1px;color:#798982}.chip{display:inline-flex;align-items:center;gap:7px;border:1px solid #cbd9d0;padding:7px 11px;border-radius:100px;font-size:11px;font-weight:700;background:#fff}
.chip::before{content:'';width:7px;height:7px;border-radius:50%;background:#249b66}.hero{padding:44px 0 28px;display:flex;justify-content:space-between;align-items:flex-end;gap:22px}
.kicker{font-size:11px;letter-spacing:2.7px;color:#d0663a;font-weight:850}h1{font-size:clamp(35px,3.7vw,55px);letter-spacing:-2px;line-height:1.08;margin:13px 0;font-weight:800}
.hero p{color:#64736d;max-width:630px;margin:12px 0 0}.hero-note{font-size:11px;color:#64736d;max-width:210px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin:19px 0 36px}
.metric{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 20px}.metric b{font-size:27px;letter-spacing:-1px;display:block}.metric small{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#789086}
.section-heading{display:flex;align-items:end;justify-content:space-between;margin:18px 0}.section-heading h2{font-size:25px;letter-spacing:-.7px;margin:0}.section-heading p{color:#75857c;font-size:12px;margin:0}
.concepts{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:19px}.concept-wrap{min-width:0}.art{aspect-ratio:4/5;min-height:0;display:flex;flex-direction:column;padding:clamp(13px,1.65vw,27px);overflow:hidden;position:relative;border-radius:10px;color:#fff;box-shadow:0 7px 25px #102c2915}
.art-emerald{background:#073e35}.art-midnight{background:#14293f}.art-terracotta{background:#734331}
.art::after{content:'';position:absolute;width:330px;height:330px;border:1px solid #ffffff18;border-radius:50%;right:-200px;top:40px;pointer-events:none}
.art-top,.art-bottom,.art-contact{display:flex;align-items:center;justify-content:space-between;gap:9px}.wordmark{letter-spacing:1.5px;display:flex;flex-direction:column;line-height:1}.wordmark b{font-size:clamp(14px,1.4vw,20px)}.wordmark small{font-size:8px;letter-spacing:1.8px;margin-top:5px}
.edition{font-size:8px;letter-spacing:1.5px;opacity:.66}.art-copy{margin:clamp(15px,1.8vw,26px) 0 clamp(12px,1.7vw,23px)}
.art-eyebrow{font-size:9px;letter-spacing:2px;font-weight:800;color:#ffbd8e}.art h3{font-size:clamp(20px,2.05vw,35px);letter-spacing:-1.25px;line-height:1.06;margin:10px 0}.art-copy p{font-size:clamp(10px,0.95vw,13px);margin:11px 0 0;color:#e5eae6;max-width:330px}
.gate-frame{position:relative;margin-top:auto;background:#f2f1e9;border:5px solid #ffffff19;padding:5px;min-height:90px;display:flex;align-items:center;justify-content:center;overflow:hidden}
.gate-frame img{width:100%;height:auto;max-height:100%;object-fit:contain;display:block}.gate-caption{position:absolute;bottom:0;left:0;right:0;padding:3px 5px;background:#092b2acb;font-size:7px;letter-spacing:.65px;text-align:center}
.art-bottom{margin-top:clamp(13px,1.5vw,23px);font-size:clamp(10px,.95vw,14px);font-weight:750;border-top:1px solid #ffffff3a;padding:13px 0 0}.art-arrow{font-size:22px}.art-contact{margin-top:10px;font-size:clamp(8px,.75vw,11px);font-weight:650;color:#f2e5dc}
.concept-meta{display:flex;align-items:center;justify-content:space-between;gap:7px;margin-top:15px}.concept-number{font-size:10px;font-weight:800;color:#b56d45;letter-spacing:1.5px}.concept-meta h4{font-size:15px;margin:2px 0 0}.status{border-radius:30px;background:#ede5d2;color:#775c2b;font-size:10px;padding:5px 10px;white-space:nowrap}
.micro{font-size:10px;color:#7b8b84;margin:10px 0}.review-controls{display:flex;gap:7px;flex-wrap:wrap}.review-controls button{border-radius:7px;padding:8px 12px;border:1px solid var(--line);background:#fff;font-size:11px;font-weight:750;color:#31534a}
.review-controls .approve{background:#174a3d;color:#fff;border-color:#174a3d}.review-controls .reject{color:#a44c43}
.lower{display:grid;grid-template-columns:1.5fr 1fr;gap:19px;margin:28px 0}.panel{background:white;border:1px solid var(--line);border-radius:12px;padding:24px}.panel h2{font-size:21px;margin:0 0 7px;letter-spacing:-.4px}.panel p{color:#6d7c74;margin:0 0 20px;font-size:12px}
.scenes{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}.scene{background:#eef3ef;border-radius:9px;padding:14px 11px;border-top:3px solid #d87749;min-height:220px}.scene b{color:#cb6c43;font-size:10px;letter-spacing:.5px}.scene h3{font-size:13px;line-height:1.3;margin:15px 0 7px}.scene p{font-size:10px;color:#738077}.cta-box{background:#103b32;color:#fff;border-radius:10px;padding:23px;margin:15px 0}
.cta-box strong{font-size:19px}.cta-box p{color:#c3d7ce;font-size:12px;margin:9px 0 18px}.primary{background:var(--orange);color:white;border:0;border-radius:7px;padding:11px 15px;font-weight:750;text-decoration:none;display:inline-block;font-size:12px}.secondary{background:white;color:#31534a;border:1px solid #c9d6ce;border-radius:7px;padding:10px 15px}
.eventline{display:flex;justify-content:space-between;gap:10px;padding:10px 0;border-bottom:1px solid #e4eae4;font-size:12px}.eventline span{color:#819087}
.publish{display:flex;align-items:center;justify-content:space-between;gap:20px;border:1px solid #e8d4ce;background:#fff8f5;border-radius:12px;padding:19px 24px;margin-top:18px}.publish h3{margin:0;font-size:16px}.publish p{margin:3px 0 0;font-size:12px;color:#826c67}
button:disabled{opacity:.5;cursor:not-allowed}.footer{font-size:11px;color:#84928a;margin-top:20px}.toast{position:fixed;bottom:24px;right:24px;background:#183d34;color:white;padding:15px 19px;border-radius:9px;box-shadow:0 8px 35px #0003;z-index:9;max-width:380px;display:none}
.ai-workspace{margin-bottom:34px;border-top:3px solid var(--orange)}.ai-workspace .section-heading{margin-top:0}.ai-form{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;align-items:end}.ai-form label{display:flex;flex-direction:column;gap:7px;font-size:11px;font-weight:800;color:#51665d;letter-spacing:.2px}.ai-form select,.ai-form textarea{border:1px solid #cedbd2;border-radius:8px;padding:12px;font:13px system-ui;background:#f8faf8;width:100%;color:#263c34}.ai-form .ai-brief{grid-column:1/-1}.ai-form textarea{resize:vertical;min-height:80px}.ai-form button{grid-column:1/-1;justify-self:start}.ai-feedback{font-size:11px;color:#637a6d;margin-top:14px}.ai-results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px;margin-top:16px}.ai-result{border:1px solid #d9e4dc;border-radius:10px;background:#f8faf7;padding:17px;min-width:0}.ai-result h3{font-size:19px;letter-spacing:-.5px;line-height:1.16;margin:8px 0}.ai-result p{font-size:12px;margin:8px 0;color:#3a5048}.ai-result .ai-meta{font-size:10px;letter-spacing:.8px;color:#a76541;font-weight:800}.ai-result .issues{color:#9c492e;font-size:11px}.ai-result .ai-buttons{display:flex;gap:7px;flex-wrap:wrap;margin-top:17px}.ai-buttons button{padding:8px 10px;border:1px solid #c9d6ce;border-radius:6px;background:white;color:#123b32;font-weight:750;font-size:11px}.ai-buttons .approve{background:#174a3d;color:white}.ai-buttons button:disabled{opacity:.45}.ai-result .result-status{font-weight:800;font-size:11px;margin:9px 0 0;color:#637b6d}@media(max-width:1050px){.ai-form{grid-template-columns:repeat(2,1fr)}.ai-results{grid-template-columns:1fr}}@media(max-width:1200px){aside{width:190px}main{margin-left:190px;padding:0 22px}.concepts{gap:12px}.lower{grid-template-columns:1fr}.art{padding:14px}}@media(max-width:850px){aside{position:static;width:auto;padding:15px;display:block}nav{margin:12px 0 0;display:flex;overflow:auto}.nav-bottom{display:none}main{margin-left:0}.concepts{grid-template-columns:1fr;max-width:500px;margin:auto}.metrics{grid-template-columns:repeat(2,1fr)}.scenes{grid-template-columns:repeat(2,1fr)}.hero{display:block}}
"""

@router.get('/director-demo',response_class=HTMLResponse)
def director_demo():
    verified_master()
    cards=''.join(concept_html(c) for c in CONCEPTS)
    plan=director_storyboard()
    scenes=''.join('<div class="scene"><b>'+escape(s['seconds'])+'</b><h3>'+
      escape(s['on_screen'])+'</h3><p>'+escape(s['visual'])+'</p></div>' for s in plan['scenes'])
    role='Director' if current_actor()=='Director' else 'Operator · read-only'
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Matrix 360 · Lakhotia Director Preview</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>'''+CSS+'''</style></head><body>
    <aside><div class="brand">MATRIX<span style="color:#df784d">360</span><small>MARKETING INTELLIGENCE</small></div>
    <nav><a class="active" href="#overview">◫ &nbsp; Overview</a>
    <a href="#ai-studio">✦ &nbsp; AI Content Studio</a><a href="#concepts">▣ &nbsp; Creative Studio</a><a href="#storyboard">▷ &nbsp; Video Storyboard</a>
    <a href="#consultation">↗ &nbsp; Conversion & Tracking</a><a href="#approval">✓ &nbsp; Director Approval</a></nav>
    <div class="nav-bottom">CONTROLLED PILOT · 16 OCT 2026<br>Architectural source locked<br>No direct social publishing</div></aside>
    <main id="overview"><div class="topbar"><span class="crumb">CLIENT WORKSPACE &nbsp;/&nbsp; LAKHOTIA INDUSTRIAL COMPLEX</span>
    <span class="chip">'''+escape(role)+''' · Protected pilot</span></div>
    <section class="hero"><div><div class="kicker">DIRECTOR DEMONSTRATION / 16 OCTOBER 2026</div>
    <h1>A smarter way to<br>move your brand forward.</h1>
    <p>One connected campaign workspace. Architecturally accurate creative concepts, storyboard planning, consultation journeys and Director-controlled approvals.</p></div>
    <div class="hero-note">DEMO MODE<br>Three pre-composed concepts · Original verified architectural master · No external publishing</div></section>
    <div class="metrics"><div class="metric"><b>03</b><small>Campaign concepts</small></div>
    <div class="metric"><b>30s</b><small>Video storyboard</small></div>
    <div class="metric"><b>01</b><small>Tracked consultation CTA</small></div>
    <div class="metric"><b>LOCKED</b><small>Architectural source</small></div></div>
    <section id="ai-studio" class="panel ai-workspace">
      <div class="section-heading"><div><div class="kicker">NEW / AI CONTENT GENERATION</div>
        <h2>Generate fresh campaign ideas with AI</h2></div><span class="chip">Director-triggered · Text only</span></div>
      <p>Enter a brief and generate three new, distinct campaign directions using the configured model. Outputs are AI-written drafts — not prewritten templates — and remain unapproved until reviewed. Original architectural imagery is always locked.</p>
      <form id="ai-form" class="ai-form">
        <label class="ai-brief">What should the campaign communicate?
          <textarea name="brief" minlength="15" maxlength="900" required rows="3"
            placeholder="e.g. Generate three non-generic B2B campaign angles for manufacturers planning a West Bengal expansion, focusing on decision confidence and consultation.">Create three fresh campaign concepts focused on why manufacturers should consider careful industrial land planning before expansion in West Bengal.</textarea>
        </label>
        <label>Target audience<select name="audience"><option>Manufacturing businesses</option><option>Warehousing operators</option><option>Logistics and 3PL</option><option>Industrial investors and occupiers</option></select></label>
        <label>Objective<select name="objective"><option>Consultation enquiries</option><option>Awareness</option><option>Thought leadership</option></select></label>
        <label>Channel<select name="platform"><option>Instagram</option><option>LinkedIn</option></select></label>
        <label>AI model<select name="provider"><option value="openai">OpenAI · GPT-4.1-mini</option><option value="groq">Groq · if configured</option></select></label>
        <button class="primary" type="submit" id="ai-submit">✦ Generate 3 AI concepts</button>
      </form>
      <div id="ai-feedback" class="ai-feedback" role="status">AI requests may incur model API charges. No image generation, sends or publishing.</div>
      <div id="ai-output" class="ai-results" aria-live="polite"></div>
    </section>
    <section id="concepts"><div class="section-heading"><div><div class="kicker">01 / CREATIVE STUDIO</div>
    <h2>Three campaign directions</h2></div><p>4:5 visual concepts · Exact verified gate master · Original artwork untouched</p></div>
    <div class="concepts">'''+cards+'''</div></section>
    <div class="lower"><section id="storyboard" class="panel"><div class="kicker">02 / VIDEO PRODUCTION</div>
    <h2>30-second promotional film</h2><p>Production-ready shot plan and voiceover brief — storyboard only, not a rendered video.</p>
    <div class="scenes">'''+scenes+'''</div><p style="margin-top:16px">
    <a href="/api/director-demo/storyboard">View full timed scenes & voiceover ↗</a>
    </p></section><section id="consultation" class="panel"><div class="kicker">03 / CONVERSION INTELLIGENCE</div>
    <h2>Consultation journey</h2><p>Tracked outbound visit with campaign UTMs. Counts are clicks, not confirmed enquiries or qualified leads.</p>
    <div class="cta-box"><strong>Planning your next industrial move?</strong>
    <p>Discuss your manufacturing, warehousing or logistics land requirement with Lakhotia Group.</p>
    <a class="primary" href="/go/consultation/'''+CAMPAIGN_ID+'''" target="_blank" rel="noopener">Request consultation ↗</a></div>
    <div class="eventline"><span>Tracked outbound clicks</span><strong id="clicks">—</strong></div>
    <div class="eventline"><span>UTM campaign</span><strong>lakhotia_poc_consultation</strong></div>
    <div class="eventline"><span>Qualified enquiries</span><strong>Not measured</strong></div>
    <button class="secondary" type="button" onclick="refresh()">Refresh tracking</button>
    </section></div>
    <section id="approval" class="publish"><div><div class="kicker">04 / GOVERNANCE & RELEASE CONTROL</div>
    <h3>Publishing is blocked until production authorization exists.</h3>
    <p>Director approvals are review decisions only. No connected social publisher, WhatsApp sender or ad account executes from this demo.</p></div>
    <button class="secondary" type="button" onclick="attemptPublish()">Test publishing safeguard</button></section>
    <div class="footer">Matrix 360 · Internal client demonstration · Illustrative architectural source is unchanged · Approvals and click counters currently use disposable preview storage.</div>
    </main><div id="toast" class="toast" role="status"></div>
    <script>
    const notify=(message)=>{const box=document.getElementById('toast');box.textContent=message;box.style.display='block';setTimeout(()=>box.style.display='none',5400);};
    async function refresh(){
      try{const res=await fetch('/api/director-demo/status',{cache:'no-store'});
        if(!res.ok)throw Error('Status unavailable');const data=await res.json();
        document.getElementById('clicks').textContent=data.cta_metrics.tracked_redirect_visits;
        for(const [id,review] of Object.entries(data.reviews)){
          const label=document.getElementById('status-'+id);
          if(label)label.textContent=review.status.replaceAll('_',' ');
        }
      }catch(e){notify('Unable to read current demo state');}
    }
    async function review(id,decision){
      const note=decision==='revision_requested'?prompt('What should be revised?'):
                 (decision==='rejected'?prompt('Rejection reason (optional):',''):'');
      if(note===null)return;
      const body=new URLSearchParams({decision,note:note||''});
      const res=await fetch('/api/director-demo/concepts/'+id+'/review',{method:'POST',body});
      let data;try{data=await res.json()}catch{data={detail:'Action failed'}};
      if(!res.ok){notify(data.detail||'Director authorization required');return}
      notify('Concept 0'+id+' '+decision.replaceAll('_',' ')+'. Not published.');
      refresh();
    }
    async function attemptPublish(){
      const res=await fetch('/api/director-demo/publish',{method:'POST'});
      let data;try{data=await res.json()}catch{data={detail:'Publishing unavailable'}}
      notify(res.status===409?'Publishing safely blocked: '+data.detail:
        res.status===403?'Publishing blocked: Director authorization required.':
        'Publishing unavailable.');
    }
    let activeBatch=null;
    const aiForm=document.getElementById('ai-form');
    const resultContainer=document.getElementById('ai-output');
    function safeText(s){return String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}
    function showAi(data){
      activeBatch=data.id;
      resultContainer.innerHTML=(data.candidates||[]).map((c,i)=>{
        const check=(data.checks||[])[i]||{passed:false,issues:['Compliance not evaluated']};
        return '<article class="ai-result"><div class="ai-meta">AI CONCEPT 0'+(i+1)+' · '+safeText(data.provider)+' · '+safeText(c.pillar)+'</div>'+
        '<h3>'+safeText(c.headline)+'</h3><p>'+safeText(c.subheadline)+'</p>'+
        '<p>'+safeText(c.caption)+'</p><div class="ai-meta">CREATIVE DIRECTION</div><p>'+safeText(c.creative_guidance)+'</p>'+
        '<div class="'+(check.passed?'result-status':'issues')+'">'+(check.passed?'Automated screen passed · Director review required':'Flagged: '+safeText((check.issues||[]).join('; ')))+'</div>'+
        '<div class="result-status" id="ai-state-'+(i+1)+'">Awaiting Director review</div>'+
        '<div class="ai-buttons"><button type="button" class="approve" '+(check.passed?'':'disabled')+' onclick="reviewAi('+(i+1)+',\'approved\')">Approve</button>'+
        '<button type="button" onclick="reviewAi('+(i+1)+',\'rejected\')">Reject</button>'+
        '<button type="button" onclick="reviewAi('+(i+1)+',\'revision_requested\')">Request revision</button></div></article>';
      }).join('');
    }
    aiForm.addEventListener('submit',async e=>{
      e.preventDefault();
      const btn=document.getElementById('ai-submit');
      btn.disabled=true;btn.textContent='Generating AI concepts…';
      document.getElementById('ai-feedback').textContent='Requesting three new text concepts. Verified architecture is not sent for image editing.';
      try{
        const res=await fetch('/api/director-demo/ai/generate',{method:'POST',body:new FormData(aiForm)});
        const payload=await res.json();
        if(!res.ok){throw Error(payload.detail||'AI generation failed')}
        showAi(payload);
        document.getElementById('ai-feedback').textContent='Generated using '+payload.provider+' / '+payload.model+'. Stored as unapproved text drafts in preview database. No publishing.';
      }catch(err){document.getElementById('ai-feedback').textContent='Generation failed: '+err.message;}
      finally{btn.disabled=false;btn.textContent='✦ Generate 3 AI concepts';}
    });
    async function reviewAi(option,decision){
      if(!activeBatch){notify('Generate AI content first');return;}
      const note=decision==='revision_requested'?prompt('Describe the required revision:'):
        decision==='rejected'?prompt('Rejection reason (optional):',''):'';
      if(note===null)return;
      const body=new URLSearchParams({decision,note:note||''});
      try{
        const res=await fetch('/api/director-demo/ai/batches/'+encodeURIComponent(activeBatch)+'/'+option+'/decision',{method:'POST',body});
        const payload=await res.json();
        if(!res.ok)throw Error(payload.detail||'Review declined');
        document.getElementById('ai-state-'+option).textContent='Director decision: '+decision.replaceAll('_',' ')+'. Not published.';
        notify('AI concept 0'+option+': '+decision+'. Publishing remains blocked.');
      }catch(err){notify(err.message);}
    }
    refresh();
    </script></body></html>'''
    return HTMLResponse(page)
