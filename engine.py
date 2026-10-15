"""Content engine: optional model API, strict claims validation, and local PNG renderer."""
import json, os, re, textwrap, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).parent
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
BRAND='#073d34'; ORANGE='#ed5c24'; NAVY='#122a48'

def create(profile, topic, objective, platform, fallback):
    """Optional AI; offline deterministic fallback when no API key is configured."""
    key=os.getenv('OPENAI_API_KEY','').strip()
    if not key:
        return fallback(topic,objective,platform), 'offline_template'
    req_body={
        'model':os.getenv('MATRIX_MODEL','gpt-4.1-mini'),
        'temperature':0.5,
        'response_format':{'type':'json_object'},
        'messages':[{'role':'system','content':('Act as an industrial B2B marketing copy editor. Return JSON with candidates array of exactly 3 objects. '+
          'Each object needs option (integer 1-3), pillar, headline (max 52 chars), subheadline (max 85 chars), '+
          'caption (max 800 chars), cta, creative_guidance, objective, platform. Use only approved facts. '+
          'Never invent project facilities, delivery timelines, ROI, or imply planned amenities are operational. '+
          'Area size: 1,000 bighas under development; expansion plan 2,500+ bighas. '+
          'Keep readable, non-generic content. Every caption includes +91 74500 08999 and www.lakhotiaindustrialcomplex.com. '+
          'Do not include 800 bighas.')},
          {'role':'user','content':json.dumps({'topic':topic,'objective':objective,'platform':platform,'approved_claims':profile['approved_claims'],'voice':profile['voice'],'audiences':profile['audiences']})}]}
    endpoint=os.getenv('MATRIX_OPENAI_ENDPOINT','https://api.openai.com/v1/chat/completions')
    request=urllib.request.Request(endpoint, data=json.dumps(req_body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'},method='POST')
    try:
        with urllib.request.urlopen(request,timeout=25) as response: raw=json.loads(response.read())
        items=json.loads(raw['choices'][0]['message']['content'])['candidates']
        if not isinstance(items,list) or len(items)!=3: raise ValueError('Expected three candidates')
        required={'option','pillar','headline','subheadline','caption','cta','creative_guidance'}
        if any(not isinstance(c,dict) or not required.issubset(c) for c in items):raise ValueError('Missing candidate fields')
        for i,c in enumerate(items,1):
            if not all(isinstance(c[k],str) and c[k].strip() for k in ('headline','caption','cta','pillar')):raise ValueError('Empty or invalid content field')
            c['option']=i;c['platform']=platform;c['objective']=objective;c['generator']='openai_api'
        return items,'openai_api'
    except Exception as exc:
        raise RuntimeError('Model generation failed; no silently substituted AI output: '+str(exc)) from exc

def verify(items):
    issues=[]
    for c in items:
        text=' '.join(str(v) for v in c.values())
        errors=[]
        if re.search(r'(?<!\d)800\s*bighas\b',text,re.I):errors.append('Outdated claim: 800 bighas')
        if re.search(r'\b(operational|completed|already open)\s+(fuel|cng|ev charging|hotel|restaurant|weighbridge)',text,re.I):errors.append('Unverified operational facility')
        if re.search(r'\b(guaranteed returns|100\s*%\s*roi|assured appreciation)\b',text,re.I):errors.append('Unsubstantiated financial claim')
        if re.search(r'\b2500\+?\s*bighas\b|\b2,500\+?\s*bighas\b',text,re.I) and 'plan' not in text.lower() and 'expansion' not in text.lower():errors.append('Expansion not identified as planned')
        if '+91 74500 08999' not in text and '74500 08999' not in text:errors.append('Missing approved phone number')
        if 'lakhotiaindustrialcomplex.com' not in text:errors.append('Missing approved website')
        if len(str(c.get('headline','')))>70:errors.append('Headline exceeds template capacity')
        issues.append({'option':c['option'],'passed':not errors,'issues':errors,'human_approval_required':True})
    return issues

def _font(size,bold=False):return ImageFont.truetype(BOLD if bold else FONT,size)

def _wrap(draw,text,font,width):
    words=str(text).split();lines=[];line=''
    for word in words:
        candidate=(line+' '+word).strip()
        if draw.textbbox((0,0),candidate,font=font)[2]>width and line:lines.append(line);line=word
        else:line=candidate
    if line:lines.append(line)
    return lines

def render_card(candidate,path,kind=0):
    """1080x1350 proof templates. Embed exact approved image; do not redraw branding."""
    from PIL import ImageOps
    w,h=1080,1350
    palettes=[('#f7faf8','#e5efe9'),('#f8f8f5','#eaf0f6'),('#fcf8f3','#f4e9dd')]
    bg,panel=palettes[kind%3]
    im=Image.new('RGB',(w,h),bg)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,w,15),fill=ORANGE)
    logo_path=BASE/'assets'/'lakhotia_group_logo_official.png'
    if not logo_path.exists(): raise FileNotFoundError('Approved logo file missing')
    with Image.open(logo_path) as raw:
        logo=raw.convert('RGB')
        # White/off-white logo background stays within its own defined, unaltered lockup.
        logo.thumbnail((420,112),Image.Resampling.LANCZOS)
        im.paste(logo,(72,60))
    d.text((76,200),'LAKHOTIA INDUSTRIAL COMPLEX',font=_font(24,True),fill=BRAND)
    d.line((75,250,1005,250),fill='#cad9d2',width=3)
    d.rounded_rectangle((70,295,1010,895),radius=22,fill=panel)
    d.rectangle((70,295,85,895),fill=ORANGE)
    pillar=str(candidate.get('pillar','Industrial opportunity')).upper()[:45]
    d.text((126,353),pillar,font=_font(27,True),fill=ORANGE)
    d.text((126,419),['BUILT FOR BUSINESS','PLAN. SET UP. GROW.','YOUR NEXT MOVE'][kind%3],font=_font(31,True),fill=NAVY)
    y=510
    for line in _wrap(d,candidate.get('headline',''),_font(51,True),800)[:4]:
        d.text((126,y),line,font=_font(51,True),fill=BRAND)
        y+=72
    if y>825: raise ValueError('Headline exceeds template bounds')
    d.line((126,835,947,835),fill=ORANGE,width=4)
    y=942
    for line in _wrap(d,candidate.get('subheadline',''),_font(30),925)[:3]:
        d.text((77,y),line,font=_font(30),fill=NAVY); y+=48
    d.rounded_rectangle((70,1113,1010,1184),radius=12,fill=BRAND)
    d.text((100,1135),'DISCUSS YOUR INDUSTRIAL LAND REQUIREMENT',font=_font(23,True),fill='white')
    d.text((75,1210),'+91 74500 08999',font=_font(31,True),fill=BRAND)
    d.text((75,1260),'www.lakhotiaindustrialcomplex.com',font=_font(23),fill=NAVY)
    d.text((822,1322),'DESIGN PROOF',font=_font(17,True),fill='#747b7b')
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    im.save(path)
    return path


from creative_renderer_v07 import render_card_v07
render_card = render_card_v07
