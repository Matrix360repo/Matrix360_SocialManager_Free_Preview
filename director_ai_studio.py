"""Director demo AI Content Studio. Text ideation, never generative architecture.

Generates three model-authored textual campaign directions from approved claims.
Human-only release decisions, no publishing or paid image generation.
"""
import json
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Form, HTTPException
from security_roles import director_required
from engine import create, verify, get_ai_config
import reference_grid as grid
import durable_campaign_store as durable
from director_demo import verified_master

router=APIRouter()
AUDIENCES=('Manufacturing businesses','Warehousing operators','Logistics and 3PL','SME light manufacturing','MSME production units','Growing regional warehouses','Small logistics and 3PL units')
OBJECTIVES=('Awareness','Consultation enquiries','Thought leadership')
PLATFORMS=('Instagram','Facebook','LinkedIn','X-Twitter')
PROVIDERS=('openai','groq')
FORBIDDEN=[
    r'\b(?:ready to move|ready now|fully developed|fully operational|operational facilities)\b',
    r'\b(?:guaranteed|assured|risk.free|highest returns|roi)\b',
    r'\b(?:fuel station|cng station|restaurant|hotel|weighbridge)\b',
    r'\b(?:800\s*bighas)\b',
    r'\b(?:approved by government|government approved|government certified)\b',
    r'\b(?:best|largest|number one|#1)\s+(?:industrial|land|park|complex)\b',
]
FACTUAL_PATTERN=re.compile(r'\b(?:bighas?|kilometres?|kilometers?|km|acres?|hectares?|percent|%|nh[-\s]?\d+|crores?|lakhs?)\b',re.I)
APPROVED_QUANTITIES=('1,000 bighas under development','2,500+ bighas planned expansion',
                     'approx. 4 km from nh-16','approximately 4 km from nh-16',
                     '35+ years')
SAFE_SOURCE='Lakhotia Industrial Complex; Ranihati–Amta Road, Howrah, West Bengal; approximately 4 km from NH-16; industrial plots for Indian SMEs and MSMEs in light manufacturing, growing warehousing and regional logistics; free expert consultation; +91 74500 08999; lakhotiaindustrialcomplex.com. Omit all acreage claims pending factual reconfirmation.'

def connect():
    grid.DB.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(grid.DB,timeout=15)
    db.row_factory=sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS ai_campaign_batches(
        id TEXT PRIMARY KEY,created_utc TEXT NOT NULL, brief TEXT NOT NULL,
        provider TEXT NOT NULL,model TEXT NOT NULL,payload TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS ai_campaign_reviews(
        batch_id TEXT NOT NULL,option_no INTEGER NOT NULL,
        decision TEXT NOT NULL,note TEXT NOT NULL,reviewer TEXT NOT NULL,
        reviewed_utc TEXT NOT NULL,PRIMARY KEY(batch_id,option_no))""")
    db.execute("""CREATE TABLE IF NOT EXISTS ai_campaign_audit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,batch_id TEXT NOT NULL,
        option_no INTEGER NOT NULL,decision TEXT NOT NULL,note TEXT NOT NULL,
        reviewer TEXT NOT NULL,created_utc TEXT NOT NULL)""")
    db.commit()
    return db

def strict_check(candidate):
    """Conservative *screen*, not a certification of factual truth."""
    text=' '.join(str(candidate.get(x,'')) for x in
                  ('pillar','headline','subheadline','caption','cta','creative_guidance'))
    reasons=[]
    if any(re.search(p,text,re.I) for p in FORBIDDEN):
        reasons.append('Unsupported or risky site/financial claim detected')
    # Quantities must appear only as approved phrases. Copywriters can omit
    # numbers entirely; any numeric claims not on whitelist go to manual revision.
    normalized=re.sub(r'\s+',' ',text.lower()).replace('1000 bighas','1,000 bighas')
    stripped=normalized
    for approved in APPROVED_QUANTITIES:
        stripped=stripped.replace(approved,' ')
    if re.search(r'(?<!\w)(?:\d[\d,.]*\s*(?:\+|%)?\s*(?:bighas?|km|acres?|hectares?|crores?|lakhs?)|\bnh[-\s]?\d+\b)',stripped,re.I):
        reasons.append('Unverified numeric/geographic claim')
    if re.search(r'\b(?:mega[- ]?factories|mega[- ]?parks|large[- ]?scale enterprises|gigantic (?:plants|factories|complexes)|fortune 500|multinational conglomerates)\b',text,re.I):
        reasons.append('Narrative is outside the SME/MSME target audience')
    if 'lakhotiaindustrialcomplex.com' not in text.lower():reasons.append('Missing official website')
    if '74500 08999' not in text:reasons.append('Missing official telephone')
    if len(str(candidate.get('headline','')))>70:reasons.append('Headline too long')
    return {'passed':not reasons,'issues':reasons,'human_approval_required':True}

def platform_engagement(candidate):
    """Ready-to-copy platform engagement text; never an auto-publishing action."""
    headline=str(candidate.get('headline','Industrial expansion planning')).strip()[:105]
    pillar=str(candidate.get('pillar','')).lower()
    focus=('light manufacturing' if 'human' in pillar else
           'industrial utilities planning' if 'utilit' in pillar else 'industrial land planning')
    hashtags={
        'Instagram':['#LakhotiaIndustrialComplex','#SMEIndia','#MSMEIndia','#LightManufacturing','#HowrahBusiness','#WarehousePlanning','#WestBengalIndustry','#GrowingBusinesses'],
        'Facebook':['#LakhotiaIndustrialComplex','#MSMEIndia','#HowrahBusiness','#SmallBusinessGrowth','#IndustrialLand'],
        'LinkedIn':['#MSME','#SMEManufacturing','#IndustrialDevelopment','#WarehouseOperations','#WestBengalBusiness'],
        'X-Twitter':['#MSME','#SMEIndia','#Howrah','#IndustrialGrowth']
    }
    comment=(headline+'. What matters most for your next '+focus+
             ' decision—access, planning or expansion flexibility? Ask about a free expert consultation: +91 74500 08999.')
    return {platform:{'comment':comment,'hashtags':tags} for platform,tags in hashtags.items()}


def enriched_payload(payload):
    """Add four-platform comment/hashtag drafts to existing stored campaigns."""
    result=dict(payload)
    result['candidates']=[dict(c,engagement=platform_engagement(c)) for c in payload.get('candidates',[])]
    return result


def real_reel_concepts(cfg,brief,concepts):
    """Second real model call: three independent cinematographic video concepts."""
    import urllib.request
    payload={'model':cfg['model'],'temperature':0.65,'response_format':{'type':'json_object'},
      'messages':[{'role':'system','content':(
       'You are a premium industrial B2B film director. Return JSON object with '
       'reels array of EXACTLY 3 objects. Each must include headline, video_prompt, '
       'caption, platform. Video prompts must describe ACTUAL MOVING live-action '
       'authentic Indian SME industrial visual sources plus distinct kinetic graphics. '
       'Reels are motion graphics, not live-action cinema. No simple slideshows or invented Lakhotia '
       'construction, no real site representation, no logos in model footage. '
       'Each video_prompt 80-300 words. Reel 1 category architecture and '
       'infrastructure must rely on exact approved gate, never fictional site '
       'structures; reel 2 focuses authentic Indian SME workers, local industrial ' 'attire and modest operational settings; '
       'reel 3 depicts only generic illustrative utilities, IoT and technology '
       '(no claim these installations exist at Lakhotia). '
       'Include three distinct kinetic-text phases and a natural spoken '
       'narration hook for the matching business theme. '
       'Do not claim project facilities are complete; mark scenes illustrative. ' 'No mega-factories, multinational campuses or large enterprise logistics parks.'
       )},
       {'role':'user','content':json.dumps({'brief':brief,'related_social_concepts':[
         {'headline':c['headline'],'pillar':c['pillar']} for c in concepts],
         'approved_facts':SAFE_SOURCE})}]}
    req=urllib.request.Request(cfg['endpoint'],data=json.dumps(payload).encode(),
      headers={'Authorization':'Bearer '+cfg['key'],'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=40) as resp:
            raw=json.load(resp)
        reels=json.loads(raw['choices'][0]['message']['content'])['reels']
    except Exception:
        raise HTTPException(502,'Video concept AI provider failed; no substitute reels created') from None
    if (not isinstance(reels,list) or len(reels)!=3 or
        any(not isinstance(x,dict) or not 120<len(x.get('video_prompt',''))<2500 or
                not x.get('headline') for x in reels)):
        raise HTTPException(502,'Video AI provider did not return three complete motion concepts')
    if len({x['video_prompt'].lower().strip() for x in reels})!=3:
        raise HTTPException(502,'Video AI repeated a concept')
    for i,x in enumerate(reels,1):x['option']=i
    return reels

def create_ai_batch(brief,audience,objective,platform,provider):
    director_required()
    if not 15<=len(brief.strip())<=900:
        raise HTTPException(422,'Brief must contain 15–900 characters')
    if audience not in AUDIENCES or objective not in OBJECTIVES or platform not in PLATFORMS:
        raise HTTPException(422,'Invalid target audience, objective or platform')
    if provider not in PROVIDERS:
        raise HTTPException(422,'Explicit AI provider required; no offline template masquerading as AI')
    # Prove source bytes are available before any cost-bearing model call.
    verified_master()
    try:
        cfg=get_ai_config(requested=provider)
    except RuntimeError:
        raise HTTPException(503,'Selected AI provider is not configured')
    if not cfg:
        raise HTTPException(503,'AI provider unavailable')
    if re.search(r'\b(?:mega[- ]?factory|mega[- ]?complex|large[- ]?scale enterprise|multinational conglomerate|fortune 500)\b',brief,re.I):
        raise HTTPException(422,'Campaign audience is restricted to SME/MSME and growing regional industry')
    full_topic=('Campaign creative brief: '+brief.strip()+
       '\nMANDATORY SCALE: India-based SMEs/MSMEs, light manufacturing, small workshops and growing modest warehousing/3PL businesses ONLY; no huge plants, enterprise campuses or mega warehouses. Segment: '+audience+
       '\nCreate three genuinely DIFFERENT angles and headlines. Use only these claims: '+SAFE_SOURCE+
       '\nDo not imply construction is complete. Cast authentic Indian adults in locally appropriate professional or safety workwear with realistic Howrah-area small-workshop environments. Preserve the unaltered original architectural gate.'+
       '\nAvoid all acreage and bigha figures pending Director reconfirmation; no new facilities, ROI, rankings or invented numerical claims.'+
       '\nSTRICT CATEGORY SPLIT for generated concepts: #1 Architecture & Infrastructure (use existing approved Lakhotia gate artwork; do not generate a new gate or a fictitious master plan); #2 Human Element & Operations (authentic one/two-person workplace or industrial planning scene); #3 Facilities, Utilities & Technology (generic real industrial instruments or utility technology, zero people; label any such scene as illustrative and NOT installed Lakhotia infrastructure). Use separate storytelling, unique camera style and copy in each category.'+
       '\nAvoid repeated faces, duplicate people, extra arms or fingers, cutout photographic seams, impossible pipe connections and unrealistic logistics scenes.'+
       '\nNever generate, depict or redraw the Lakhotia complex itself. Its official gate is a separate immutable asset and must not be used as a generative reference.')
    # No fallback: failure must be visible, never falsely reported as AI.
    def no_fallback(*args):raise RuntimeError('AI unavailable; no fake generated output')
    try:
        concepts,used=create(
          {'approved_claims':[SAFE_SOURCE],
           'voice':'Authentic Indian SME/MSME industrial consulting; practical, precise, locally credible',
           'audiences':[audience]},
           full_topic,objective,platform,no_fallback,requested_provider=provider)
    except Exception as exc:
        raise HTTPException(502,'AI text generation unavailable; no concepts were saved') from exc
    if used not in ('openai_api','groq_api') or len(concepts)!=3:
        raise HTTPException(502,'AI did not deliver three complete concepts')
    directions=[re.sub(r'\s+',' ',str(c.get('creative_guidance','')).strip().lower()) for c in concepts]
    if any(len(x)<40 for x in directions) or len(set(directions))!=3:
        raise HTTPException(502,'AI did not provide three distinct production-ready visual directions')
    common=verify(concepts)
    reviewed=[]
    for i,c in enumerate(concepts):
        if len(json.dumps(c))>7000:
            raise HTTPException(502,'AI response exceeded content limits')
        strict=strict_check(c)
        issues=list(dict.fromkeys(common[i]['issues']+strict['issues']))
        reviewed.append({'option':i+1,'passed':not issues,'issues':issues,
                         'human_approval_required':True})
    reels=real_reel_concepts(cfg,brief,concepts)
    concepts=[dict(c,engagement=platform_engagement(c)) for c in concepts]
    ident=str(uuid.uuid4())
    timestamp=datetime.now(timezone.utc).isoformat()
    if durable.is_configured():
        try:
            durable.save_batch(ident,timestamp,brief.strip(),used,cfg['model'],
                {'candidates':concepts,'checks':reviewed,'reels':reels})
        except durable.CampaignStoreError as exc:
            raise HTTPException(503,str(exc)) from None
    with connect() as db:
        db.execute('INSERT INTO ai_campaign_batches VALUES (?,?,?,?,?,?)',
          (ident,timestamp,brief.strip(),used,cfg['model'],
           json.dumps({'candidates':concepts,'checks':reviewed},ensure_ascii=False)))
        db.commit()
    from production_media import launch
    launch(ident,concepts,reels)
    return {'id':ident,'provider':used,'model':cfg['model'],'candidates':concepts,'reels':reels,
            'checks':reviewed,'publication_status':'blocked','archival_scope':'private_supabase' if durable.is_configured() else 'ephemeral_demo'}

@router.post('/api/director-demo/ai/generate')
def generate(brief:str=Form(...),audience:str=Form('Manufacturing businesses'),
             objective:str=Form('Consultation enquiries'),
             platform:str=Form('Instagram'),provider:str=Form('openai')):
    return create_ai_batch(brief,audience,objective,platform,provider)

@router.get('/api/director-demo/ai/batches')
def batches():
    if durable.is_configured():
        try:return {'batches':durable.list_batches(),'durable':True}
        except durable.CampaignStoreError as exc:raise HTTPException(503,str(exc)) from None
    with connect() as db:
        rows=db.execute('SELECT id,created_utc,brief,provider,model FROM ai_campaign_batches ORDER BY created_utc DESC LIMIT 8').fetchall()
    return {'batches':[dict(x) for x in rows],'durable':False}

@router.get('/api/director-demo/ai/batches/{batch_id}')
def batch_detail(batch_id:str):
    try:ident=str(uuid.UUID(batch_id))
    except ValueError:raise HTTPException(404,'Unknown generation batch')
    if durable.is_configured():
        try:
            row=durable.get_batch(ident)
            decisions=durable.get_reviews(ident) if row else []
            reel_decisions=durable.reel_reviews(ident) if row else []
        except durable.CampaignStoreError as exc:
            raise HTTPException(503,str(exc)) from None
        if row is None:raise HTTPException(404,'Unknown campaign batch')
        return {'id':ident,'brief':row['brief'],'provider':row['provider'],'model':row['model'],
                **enriched_payload(row['payload']),'reviews':{str(x['option_no']):{'decision':x['decision'],'note':x['note']} for x in decisions},
                'reel_reviews':{str(x['option_no']):{'decision':x['decision'],'note':x['note']} for x in reel_decisions},
                'publishing':'disabled','durable':True}
    with connect() as db:
        row=db.execute('SELECT * FROM ai_campaign_batches WHERE id=?',(ident,)).fetchone()
        decisions=db.execute('SELECT option_no,decision,note FROM ai_campaign_reviews WHERE batch_id=?',(ident,)).fetchall()
    if row is None:raise HTTPException(404,'Batch no longer exists (preview storage resets)')
    return {'id':ident,'brief':row['brief'],'provider':row['provider'],'model':row['model'],
            **enriched_payload(json.loads(row['payload'])),
            'reviews':{str(x['option_no']):{'decision':x['decision'],'note':x['note']} for x in decisions},
            'publishing':'disabled','durable':False}

@router.post('/api/director-demo/ai/batches/{batch_id}/{option}/decision')
def decide(batch_id:str,option:int,decision:str=Form(...),note:str=Form('')):
    director_required()
    if option not in (1,2,3):raise HTTPException(404,'Option must be 1–3')
    if decision not in ('approved','rejected','revision_requested'):
        raise HTTPException(422,'Unknown decision')
    if len(note)>500 or (decision=='revision_requested' and not note.strip()):
        raise HTTPException(422,'Revision requests require bounded feedback')
    verified_master()
    data=batch_detail(batch_id)
    check=data['checks'][option-1]
    if decision=='approved' and not check['passed'] and not note.strip().startswith('Director factual sign-off:'):
        raise HTTPException(409,'Flagged factual claims require an explicit Director factual sign-off in the review note')
    now=datetime.now(timezone.utc).isoformat()
    if durable.is_configured():
        try:durable.save_decision(batch_id,option,decision,note.strip(),now)
        except durable.CampaignStoreError as exc:raise HTTPException(503,str(exc)) from None
    with connect() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute("""INSERT INTO ai_campaign_reviews VALUES(?,?,?,?,?,?)
           ON CONFLICT(batch_id,option_no) DO UPDATE SET decision=excluded.decision,
           note=excluded.note,reviewer=excluded.reviewer,reviewed_utc=excluded.reviewed_utc""",
           (batch_id,option,decision,note.strip(),'Director',now))
        db.execute('INSERT INTO ai_campaign_audit(batch_id,option_no,decision,note,reviewer,created_utc) VALUES(?,?,?,?,?,?)',
           (batch_id,option,decision,note.strip(),'Director',now))
        db.commit()
    return {'batch_id':batch_id,'option':option,'decision':decision,
            'publication_authorized':False,'reviewer':'Director'}

@router.post('/api/director-demo/ai/batches/{batch_id}/reels/{option}/decision')
def decide_reel(batch_id:str,option:int,decision:str=Form(...),note:str=Form('')):
    director_required()
    if option not in (1,2,3):raise HTTPException(404,'Unknown reel')
    if decision not in ('approved','rejected','revision_requested'):
        raise HTTPException(422,'Unknown review action')
    if len(note)>500 or (decision=='revision_requested' and not note.strip()):
        raise HTTPException(422,'Revision request requires a note')
    data=batch_detail(batch_id)
    if len(data.get('reels',[]))!=3:
        raise HTTPException(409,'No generated reel found in this batch')
    if decision=='approved' and not data['checks'][option-1]['passed'] and not note.strip().startswith('Director factual sign-off:'):
        raise HTTPException(409,'Flagged factual claims require an explicit Director factual sign-off in the review note')
    if not durable.is_configured():
        raise HTTPException(503,'Private durable approvals must be configured')
    now=datetime.now(timezone.utc).isoformat()
    try:durable.save_reel_decision(batch_id,option,decision,note.strip(),now)
    except durable.CampaignStoreError as exc:raise HTTPException(503,str(exc)) from None
    return {'option':option,'kind':'reel','decision':decision,'reviewer':'Director',
            'publication_authorized':False,'persisted':True}
