"""Content engine: optional model API, strict claims validation, and local PNG renderer."""
import json, os, re, textwrap, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).parent
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
BRAND='#073d34'; ORANGE='#ed5c24'; NAVY='#122a48'

def clean_key(val):
    """Clean and validate API key string, stripping quotes, spaces, and ignoring placeholders."""
    if not val:
        return ''
    val = str(val).strip().strip('"').strip("'")
    if val.lower().startswith('bearer '):
        val = val[7:].strip()
    # Check for placeholder strings entered in templates or Render dashboard
    if any(placeholder in val.lower() for placeholder in ('replace', 'your_key', 'your-key', 'todo', 'none', 'null', 'undefined', '<your')):
        return ''
    return val

def get_ai_config(requested=None):
    """Detect whether Groq or OpenAI is configured, returning a configuration dict or None."""
    openai_key = clean_key(os.getenv('OPENAI_API_KEY', ''))
    groq_key = clean_key(os.getenv('GROQ_API_KEY', ''))
    preferred = (requested or os.getenv('MATRIX_AI_PROVIDER', '')).strip().lower()

    if preferred == 'offline':
        return None

    if preferred == 'groq':
        if not groq_key:
            raise RuntimeError("GROQ_API_KEY is not configured or is a placeholder. Please set a valid Groq key in Render Environment Variables.")
        provider = 'groq'
    elif preferred == 'openai':
        if not openai_key:
            raise RuntimeError("OPENAI_API_KEY is not configured or is a placeholder. Please set a valid OpenAI key in Render Environment Variables.")
        provider = 'openai'
    elif groq_key and not openai_key:
        provider = 'groq'
    elif openai_key and not groq_key:
        provider = 'openai'
    elif groq_key and openai_key:
        # Both keys configured: default to Groq (blazing fast and free/economical) unless OpenAI is explicitly chosen
        provider = 'openai' if preferred == 'openai' else 'groq'
    else:
        return None

    if provider == 'groq':
        endpoint = os.getenv('GROQ_ENDPOINT', 'https://api.groq.com/openai/v1/chat/completions').strip()
        model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile').strip()
        return {
            'provider': 'groq',
            'key': groq_key,
            'endpoint': endpoint,
            'model': model,
            'generator_name': 'groq_api'
        }
    else:
        endpoint = os.getenv('MATRIX_OPENAI_ENDPOINT', 'https://api.openai.com/v1/chat/completions').strip()
        model = os.getenv('MATRIX_MODEL', 'gpt-4.1-mini').strip()
        return {
            'provider': 'openai',
            'key': openai_key,
            'endpoint': endpoint,
            'model': model,
            'generator_name': 'openai_api'
        }

def _call_model(cfg, profile, topic, objective, platform):
    provider = cfg['provider']
    key = cfg['key']
    endpoint = cfg['endpoint']
    model = cfg['model']
    generator_name = cfg['generator_name']

    req_body = {
        'model': model,
        'temperature': 0.5,
        'response_format': {'type': 'json_object'},
        'messages': [
            {'role': 'system', 'content': (
                'Act as an industrial B2B marketing copy editor. Return JSON with candidates array of exactly 3 objects. '
                'Each object needs option (integer 1-3), pillar, headline (max 52 chars), subheadline (max 85 chars), '
                'caption (max 800 chars), cta, creative_guidance, objective, platform. Use only approved facts. '
                'Never invent project facilities, delivery timelines, ROI, or imply planned amenities are operational. '
                'Area size: 1,000 bighas under development; expansion plan 2,500+ bighas. '
                'Keep readable, non-generic content. Every caption includes +91 74500 08999 and www.lakhotiaindustrialcomplex.com. '
                'Do not include 800 bighas.'
            )},
            {'role': 'user', 'content': json.dumps({
                'topic': topic,
                'objective': objective,
                'platform': platform,
                'approved_claims': profile['approved_claims'],
                'voice': profile['voice'],
                'audiences': profile['audiences']
            })}
        ]
    }
    headers = {
        'Authorization': 'Bearer ' + key,
        'Content-Type': 'application/json',
        'User-Agent': 'Matrix360-SocialManager/1.0'
    }
    request = urllib.request.Request(endpoint, data=json.dumps(req_body).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = json.loads(response.read().decode('utf-8'))
    items = json.loads(raw['choices'][0]['message']['content'])['candidates']
    if not isinstance(items, list) or len(items) != 3:
        raise ValueError('Expected three candidates')
    required = {'option', 'pillar', 'headline', 'subheadline', 'caption', 'cta', 'creative_guidance'}
    if any(not isinstance(c, dict) or not required.issubset(c) for c in items):
        raise ValueError('Missing candidate fields')
    for i, c in enumerate(items, 1):
        if not all(isinstance(c[k], str) and c[k].strip() for k in ('headline', 'caption', 'cta', 'pillar')):
            raise ValueError('Empty or invalid content field')
        c['option'] = i
        c['platform'] = platform
        c['objective'] = objective
        c['generator'] = generator_name
    return items, generator_name

def create(profile, topic, objective, platform, fallback, requested_provider='auto'):
    """Optional AI; offline deterministic fallback when no API key is configured or offline is requested."""
    if requested_provider == 'offline':
        return fallback(topic, objective, platform), 'offline_template'
    cfg = get_ai_config(requested=requested_provider)
    if not cfg:
        return fallback(topic, objective, platform), 'offline_template'

    try:
        return _call_model(cfg, profile, topic, objective, platform)
    except urllib.error.HTTPError as exc:
        err_msg = ""
        try:
            err_data = json.loads(exc.read().decode('utf-8', errors='replace'))
            err_msg = err_data.get('error', {}).get('message', '')
        except Exception:
            pass

        # If auto-selected and received 401 Unauthorized, try alternative provider if available
        if requested_provider in ('auto', '', None) and exc.code == 401:
            alt_provider = 'openai' if cfg['provider'] == 'groq' else 'groq'
            try:
                alt_cfg = get_ai_config(requested=alt_provider)
                if alt_cfg and alt_cfg['key']:
                    return _call_model(alt_cfg, profile, topic, objective, platform)
            except Exception:
                pass

        provider_name = cfg['provider'].upper()
        detail = f"{provider_name} API returned HTTP {exc.code} ({exc.reason})"
        if err_msg:
            detail += f": {err_msg}"
        if exc.code == 401:
            detail += f". Please verify that {provider_name}_API_KEY in your Render environment variables is valid."
        raise RuntimeError(detail) from exc
    except Exception as exc:
        raise RuntimeError(f"{cfg['provider'].upper()} model generation failed; no silently substituted AI output: " + str(exc)) from exc


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
