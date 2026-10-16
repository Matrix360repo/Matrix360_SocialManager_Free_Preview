"""Lakhotia first 48-hour POC: campaign brief -> storyboard -> tracked CTA.

No AI service, real lead capture, publishing, or video generation is claimed.
All previews remain subject to the existing Director approval workflow.
"""
import re
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from html import escape
from urllib.parse import urlencode
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from engine import get_ai_config

router=APIRouter()
BASE=Path(__file__).resolve().parent
DB=BASE/'data'/'pilot.sqlite3'
CHANNELS={'LinkedIn','Instagram'}
OBJECTIVES={'Consultation enquiries','Awareness','Thought leadership'}
CAMPAIGN_ID='lakhotia_poc_consultation'
BASE_URL='https://www.lakhotiaindustrialcomplex.com/'

def storyboard(topic,platform,objective):
    topic=topic.strip()
    if not (5<=len(topic)<=200) or any(c in topic for c in '<>{}'):
        raise HTTPException(422,'Topic must be 5–200 characters without markup')
    if platform not in CHANNELS or objective not in OBJECTIVES:
        raise HTTPException(422,'Invalid platform or objective')
    scenes=[
      {'seconds':'00–05','visual':'Approved Lakhotia logo on deep green; graphic headline, no fabricated site footage','on_screen':'Your next industrial move deserves a plan.','voiceover':'Considering industrial expansion? Start with the right questions.'},
      {'seconds':'05–11','visual':'Neutral motion typography and abstract logistics routes; no claimed operating facilities','on_screen':'Manufacturing · Warehousing · Logistics','voiceover':'Think about connectivity, operations and future capacity.'},
      {'seconds':'11–18','visual':'Simple approved-facts information graphic; planned expansion explicitly qualified','on_screen':'Ranihati–Amta Road, Howrah | Approx. 4 km from NH-16','voiceover':'Explore Lakhotia Industrial Complex in Howrah, approximately four kilometres from NH-16.'},
      {'seconds':'18–24','visual':'Official logo and restrained orange CTA panel','on_screen':'Discuss your industrial land requirements','voiceover':'Speak with the Lakhotia Group team to discuss your requirements.'},
      {'seconds':'24–30','visual':'Approved brand footer, phone and website, clear illustrative-design disclaimer','on_screen':'Call +91 74500 08999 | lakhotiaindustrialcomplex.com','voiceover':'Request a consultation. Lakhotia Industrial Complex.'}
    ]
    return {'client':'Lakhotia Industrial Complex','campaign_id':CAMPAIGN_ID,'topic':topic,
            'platform':platform,'objective':objective,'format':'9:16 vertical reel concept','duration_seconds':30,
            'production_status':'storyboard_only','status':'requires_director_approval',
            'target_audience':'Manufacturers, warehouse operators, logistics businesses and expansion decision makers',
            'lead_objective':'Industrial land consultation inquiry',
            'source_attribution':'UTM-labelled outbound visit only; no verified lead conversion',
            'scenes':scenes,'disclaimer':'Storyboard is not a playable video; scenes are illustrative plans, not proof of built site features.'}

def cta_target(campaign_id):
    if campaign_id != CAMPAIGN_ID:
        raise HTTPException(404,'Unknown campaign')
    return BASE_URL+'?'+urlencode({'utm_source':'matrix360_poc','utm_medium':'owned_creative',
                                  'utm_campaign':campaign_id})

def record_visit(campaign_id):
    # Aggregate no identifiers; disposable free-preview metrics only.
    with sqlite3.connect(DB,timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS poc_visits (campaign_id TEXT PRIMARY KEY, visits INTEGER NOT NULL DEFAULT 0, last_seen TEXT)')
        db.execute('INSERT INTO poc_visits (campaign_id,visits,last_seen) VALUES (?,1,?) ON CONFLICT(campaign_id) DO UPDATE SET visits=visits+1,last_seen=excluded.last_seen',
                   (campaign_id,datetime.now(timezone.utc).isoformat()))
        db.commit()

@router.get('/api/poc/storyboard')
def get_storyboard(topic:str='Industrial expansion planning',platform:str='Instagram',objective:str='Consultation enquiries'):
    return storyboard(topic,platform,objective)

@router.get('/api/poc/metrics')
def metrics():
    with sqlite3.connect(DB,timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS poc_visits (campaign_id TEXT PRIMARY KEY, visits INTEGER NOT NULL DEFAULT 0, last_seen TEXT)')
        row=db.execute('SELECT visits,last_seen FROM poc_visits WHERE campaign_id=?',(CAMPAIGN_ID,)).fetchone()
    return {'campaign_id':CAMPAIGN_ID,'tracked_redirect_visits':row[0] if row else 0,
            'last_visit_utc':row[1] if row else None,
            'qualified_leads':None,'note':'Redirect clicks only. Not actual leads. Ephemeral on Render Free.'}

@router.get('/go/consultation/{campaign_id}')
def tracked_cta(campaign_id:str):
    target=cta_target(campaign_id)
    record_visit(campaign_id)
    return RedirectResponse(target,status_code=302)


@router.post('/campaign-studio/create')
def create_from_studio(topic:str=Form(...),objective:str=Form('Consultation enquiries'),
                       platform:str=Form('Instagram'),provider:str=Form('offline')):
    """Browser-facing generation: reuse the validated /api/generate pipeline, then
    redirect to review rather than printing JSON. Preserve API clients unchanged.
    """
    if platform not in CHANNELS or objective not in OBJECTIVES:
        raise HTTPException(422,'Invalid campaign selection')
    if provider not in ('offline','openai'):
        raise HTTPException(422,'Unsupported studio provider')
    # Runtime import avoids an import cycle while reusing the single generation
    # and persistence implementation.
    from app import generate
    result=generate(topic=topic,objective=objective,platform=platform,provider=provider)
    draft_id=result['id']
    from uuid import UUID
    try: UUID(draft_id)
    except (ValueError,TypeError) as exc:
        raise HTTPException(502,'Generation did not return a valid draft ID') from exc
    return RedirectResponse('/draft/'+draft_id,status_code=303)

@router.get('/campaign-studio',response_class=HTMLResponse)
def studio():
    ai=get_ai_config()
    provider=ai['provider'] if ai else 'offline'
    plan=storyboard('Industrial expansion planning','Instagram','Consultation enquiries')
    cards=''.join('<div class="scene"><b>'+escape(s['seconds'])+'</b><p>'+escape(s['on_screen'])+'</p><small>'+escape(s['visual'])+'</small></div>' for s in plan['scenes'])
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><title>Matrix360 | Lakhotia Campaign Studio POC</title><style>
    body{font:16px system-ui;background:#f4f6f5;color:#123e34;margin:0}header{background:#063d34;color:white;padding:28px}
    main{max-width:960px;margin:24px auto;padding:0 20px}.panel{background:white;padding:24px;border-radius:12px;margin:18px 0}
    label{display:block;margin:10px 0}input,select{padding:12px;min-width:260px;border:1px solid #b8c5bd;border-radius:6px}
    button,.cta{padding:12px 18px;color:white;background:#e9561a;border:0;border-radius:7px;text-decoration:none;display:inline-block}
    .scene{border-left:4px solid #e9561a;padding:10px 18px;margin:12px 0;background:#f7faf9}
    small{color:#64786b}a{color:#0e6a55}
    </style></head><body><header><h1>Matrix 360 — Lakhotia Campaign Studio</h1><p>Working POC · Draft, storyboard and measurable consultation CTA · No publishing</p></header><main>
    <div class="panel"><h2>1. Generate branded creative concepts</h2>
    <p>Current configured provider: <b>'''+escape(provider)+'''</b>. Choose offline for a reproducible demonstration or OpenAI for live generation.</p>
    <form action="/campaign-studio/create" method="post"><label>Campaign topic <input name="topic" value="Industrial expansion planning" required></label>
    <label>Objective <select name="objective"><option>Consultation enquiries</option><option>Awareness</option><option>Thought leadership</option></select></label>
    <label>Channel <select name="platform"><option>Instagram</option><option>LinkedIn</option></select></label>
    <label>Generator <select name="provider"><option value="offline">Offline — no API key needed</option><option value="openai">OpenAI — once key is fixed</option></select></label>
    <button type="submit">Generate 3 concepts and PNGs</button></form><p><small>Generated concepts remain under review. Director authorization controls export.</small></p></div>
    <div class="panel"><h2>2. 30-second reel storyboard (demonstration)</h2><p><small>No playable video has been generated.</small></p>'''+cards+'''
    <p><a href="/api/poc/storyboard?topic=Industrial%20expansion%20planning">Open machine-readable storyboard</a></p></div>
    <div class="panel"><h2>3. Consultation CTA</h2><p>Tracked visit to the official Lakhotia website. This does <b>not</b> establish that a qualified inquiry occurred.</p>
    <a class="cta" href="/go/consultation/lakhotia_poc_consultation" target="_blank" rel="noopener noreferrer">Explore consultation options ↗</a>
    <p><a href="/api/poc/metrics">View aggregated click count</a></p></div>
    <div class="panel"><h2>4. Review and approval</h2><p><a href="/">Open draft review queue</a>. Final approval remains restricted to the Director.</p></div>
    </main></body></html>''')
