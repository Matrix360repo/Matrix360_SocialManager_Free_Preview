"""OpenAI/Groq-backed revision proposals for the local Matrix360 Lakhotia pilot.

Key is inherited from the parent process via OPENAI_API_KEY or GROQ_API_KEY. Never stored in project files.
Creates an unapproved version only after schema/claim checks, using the existing versioning API.
"""
import json
import os
import urllib.request
import urllib.error
from html import escape
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import revision_agent as rev
from engine import verify, get_ai_config
from visual_layouts_v12 import MODES

router = APIRouter()

@router.get('/ai-revisions/{draft_id}/{option}', response_class=HTMLResponse)
def ai_revision_page(draft_id: str, option: int):
    if option not in (1,2,3):
        raise HTTPException(404, 'Invalid option')
    with rev.dbconn() as db:
        prev = rev.latest(db, draft_id, option)
        source = json.loads(prev['candidate_json'])
        feedback = db.execute("SELECT feedback FROM creative_events WHERE draft_id=? AND option_no=? AND action='revision_requested' AND trim(feedback)!='' ORDER BY event_id DESC LIMIT 1", (draft_id, option)).fetchone()
    default = feedback['feedback'] if feedback else 'Improve composition, visual hierarchy and messaging while preserving verified brand details.'
    cfg = get_ai_config()
    if cfg:
        p_name = 'Groq' if cfg['provider'] == 'groq' else 'OpenAI'
        key_notice = f'{p_name} key detected ({cfg["model"]}) for this server session.'
        btn_label = f'Generate AI Revision ({p_name})'
        cost_notice = f'Each request uses the configured {p_name} API. The result is saved as a new, unapproved creative version; no publishing is performed. Do not enter secrets or personal data in revision instructions.'
    else:
        key_notice = 'Neither OPENAI_API_KEY nor GROQ_API_KEY is configured. Configure credentials in environment variables or Render settings.'
        btn_label = 'Generate AI Revision (API key required)'
        cost_notice = 'An active OpenAI or Groq API key is required to generate AI revisions. The result is saved as a new, unapproved creative version.'
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><title>AI Creative Revision</title><style>body{font:16px system-ui;margin:35px auto;max-width:840px;padding:20px;color:#073d34;background:#f5f7f6}article{background:white;border-radius:12px;padding:26px}textarea,input{display:block;width:95%;padding:12px;margin:12px 0}button{padding:14px 22px;background:#e9561a;color:white;border:none;border-radius:6px}small{color:#576861}</style></head><body><p><a href="/revisions/'''+escape(draft_id)+'''/'''+str(option)+'''">← Revision workspace</a></p><article><h1>AI Revision — Option '''+str(option)+'''</h1><p>Current version: '''+str(prev['version_no'])+''' · '''+escape(source.get('headline',''))+'''</p><p>'''+escape(key_notice)+'''</p><form method="post" action="/ai-revisions/'''+escape(draft_id)+'''/'''+str(option)+'''/generate"><label>Reviewer<input name="reviewer" required maxlength="100" placeholder="Tanmayi"></label><label>Revision instructions<textarea name="feedback" maxlength="3000" rows="7" required>'''+escape(default)+'''</textarea></label><button type="submit">'''+escape(btn_label)+'''</button></form><small>'''+escape(cost_notice)+'''</small></article></body></html>''')


def ai_propose(source, feedback):
    cfg = get_ai_config()
    if not cfg:
        raise HTTPException(503, 'Neither OPENAI_API_KEY nor GROQ_API_KEY is configured. Configure credentials in .env or Render dashboard.')
    provider = cfg['provider']
    key = cfg['key']
    endpoint = cfg['endpoint']
    model = cfg['model']
    system = ("You are revising a Lakhotia Industrial Complex, Howrah marketing creative. "
      "Reply with one JSON object containing only headline, subheadline, caption, cta, design_style. "
      "design_style MUST be one of editorial_split, bold_typography, planning_infographic. "
      "Act on revision feedback by changing content and selecting an appropriate design_style; "
      "never assume an actual site photograph, operational amenities, guaranteed return, or completion. "
      "Facts: Ranihati–Amta Road, Howrah, approx 4 km from NH-16. "
      "1,000 bighas under development; 2,500+ bighas planned expansion. "
      "Approved phone +91 74500 08999 and website www.lakhotiaindustrialcomplex.com. "
      "Do not use obsolete 800 bighas. Captions MUST include phone and website. "
      "Headline max 70 chars, subheadline max 250, caption max 2500, CTA max 140. "
      "This is a proposal requiring human approval.")
    body = {'model':model, 'response_format':{'type':'json_object'}, 'temperature':0.5,
        'messages':[{'role':'system','content':system},
                    {'role':'user','content':json.dumps({'existing_creative':{k:source.get(k) for k in ('headline','subheadline','caption','cta','design_style')}, 'reviewer_feedback':feedback},ensure_ascii=False)}]}
    req = urllib.request.Request(endpoint,
        data=json.dumps(body).encode('utf-8'),
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'Matrix360-SocialManager/1.0'},method='POST')
    try:
        with urllib.request.urlopen(req, timeout=50) as res:
            result=json.loads(res.read().decode('utf-8'))
        proposal=json.loads(result['choices'][0]['message']['content'])
    except urllib.error.HTTPError as exc:
        err_msg = ""
        try:
            err_data = json.loads(exc.read().decode('utf-8', errors='replace'))
            err_msg = err_data.get('error', {}).get('message', '')
        except Exception:
            pass
        detail = f"{provider.upper()} API returned HTTP {exc.code} ({exc.reason})"
        if err_msg:
            detail += f": {err_msg}"
        if exc.code == 401:
            detail += f". Please verify {provider.upper()}_API_KEY in Render environment variables."
        raise HTTPException(502, detail) from exc
    except (urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(502,f'{provider.upper()} generation failed; no revision was saved: '+str(exc)[:260]) from exc
    if not isinstance(proposal,dict):
        raise HTTPException(502,'Model did not return a JSON object')
    lengths={'headline':70,'subheadline':250,'caption':2500,'cta':140}
    for field,max_len in lengths.items():
        if not isinstance(proposal.get(field),str) or not (1<=len(proposal[field].strip())<=max_len):
            raise HTTPException(422,f'AI generated invalid {field}; no revision saved')
    if proposal.get('design_style') not in MODES:
        raise HTTPException(422,'AI generated invalid design_style; no revision saved')
    checked = {**source, **{key:proposal[key].strip() for key in lengths}}
    checked['design_style']=proposal['design_style']
    checks=verify([checked])
    if not checks[0]['passed']:
        raise HTTPException(409,'Compliance blocked AI revision: '+'; '.join(checks[0]['issues']))
    return proposal

@router.post('/ai-revisions/{draft_id}/{option}/generate')
def generate_ai_revision(draft_id:str, option:int, reviewer:str=Form(...), feedback:str=Form(...)):
    if option not in (1,2,3):raise HTTPException(404,'Invalid option')
    if not 2<=len(reviewer.strip())<=100:raise HTTPException(422,'Invalid reviewer')
    if not 5<=len(feedback.strip())<=3000:raise HTTPException(422,'Feedback must be 5-3000 characters')
    with rev.dbconn() as db:
        current=rev.latest(db,draft_id,option)
        source=json.loads(current['candidate_json'])
    proposal=ai_propose(source,feedback.strip())
    # The existing tested creator handles PNG generation, compliance, optimistic concurrency,
    # unapproved version status and persistence of the original asset.
    rev.create_revision(draft_id,option,reviewer,proposal['headline'],proposal['subheadline'],proposal['caption'],proposal['cta'],feedback,'{}'.format(proposal['design_style']))
    return RedirectResponse(f'/revisions/{draft_id}/{option}',status_code=303)
