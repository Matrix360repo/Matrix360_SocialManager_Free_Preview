"""Platform-specific, real PNG exports for Director-reviewed Lakhotia concepts.

Three distinct layouts. Concept 1 uses exact checksum-verified original gate;
concepts 2/3 use abstract functional infographic artwork, never made-up site
photography. No AI-generated or altered buildings. Four actual file dimensions.
"""
import io
import math
import hashlib
from PIL import Image, ImageDraw, ImageFont, ImageOps
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from security_roles import director_required
from director_demo import verified_master, CONCEPTS
from director_ai_studio import batch_detail

router=APIRouter()
SIZES={'Instagram':(1080,1350),'Facebook':(1200,630),'LinkedIn':(1200,627),'X-Twitter':(1600,900)}
INK='#18392f';ORANGE='#ed6c31';BLUE='#1d4265';CREAM='#f4f1e9';WHITE='#ffffff'
FACE='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BOLD='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def font(size,bold=False):
    return ImageFont.truetype(BOLD if bold else FACE,max(10,int(size)))

def lines(draw,text,size,width,bold=True):
    f=font(size,bold)
    words=str(text).strip().split()
    out=[];part=''
    for word in words:
        trial=(part+' '+word).strip()
        if part and draw.textbbox((0,0),trial,font=f)[2]>width:
            out.append(part);part=word
        else:part=trial
    if part:out.append(part)
    return out

def multiline(draw,text,at,size,width,color,leading=1.18,maxlines=4):
    x,y=at
    for ln in lines(draw,text,size,width)[:maxlines]:
        draw.text((x,y),ln,font=font(size,True),fill=color)
        y+=int(size*leading)
    return y

def brand(draw,w,h,color):
    draw.text((w*.055,h*.044),'LAKHOTIA',font=font(min(w*.042,h*.057),True),fill=color)
    draw.text((w*.057,h*.044+min(w*.047,h*.064)),'INDUSTRIAL COMPLEX',font=font(min(w*.012,h*.022),True),fill=color)

def footer(draw,w,h,color):
    draw.line((w*.05,h*.919,w*.95,h*.919),fill=color,width=max(2,int(w*.0015)))
    sz=min(w*.017,h*.025);f=font(sz,True)
    draw.text((w*.055,h*.944),'+91 74500 08999',font=f,fill=color)
    website='lakhotiaindustrialcomplex.com'
    tw=draw.textbbox((0,0),website,font=f)[2]
    draw.text((w*.945-tw,h*.944),website,font=f,fill=color)

def image_bytes(option,platform,headline=None,subheadline=None):
    if platform not in SIZES:raise HTTPException(422,'Invalid social platform')
    if option not in (1,2,3):raise HTTPException(404,'Invalid creative option')
    w,h=SIZES[platform]
    vertical=h/w>1
    titles=('LAND AT THE RIGHT PLACE FOR YOUR BUSINESS.',
            'PLAN HOW YOUR BUSINESS MOVES.',
            'BEFORE THE PLOT, KNOW THE PLAN.')
    title=(headline or titles[option-1]).strip()[:160]
    subtitle=(subheadline or (
        'Ranihati–Amta Road, Howrah · Approx. 4 km from NH-16',
        'Supply · Production · Distribution',
        'Your operations. Your space. Your expansion.'
    )[option-1]).strip()[:160]
    im=Image.new('RGB',(w,h),CREAM if option!=2 else BLUE)
    d=ImageDraw.Draw(im)
    if option==1:
        brand(d,w,h,INK)
        start=h*.145 if vertical else h*.20
        fs=min(w*.055,h*.073) if vertical else min(w*.043,h*.074)
        end=multiline(d,title,(w*.055,start),fs,w*.875,INK,maxlines=4 if vertical else 2)
        d.rounded_rectangle((w*.055,end+h*.016,w*.54,end+h*.067),radius=5,fill=ORANGE)
        d.text((w*.072,end+h*.029),'HOWRAH · INDUSTRIAL LAND',font=font(min(w*.015,h*.027),True),fill=WHITE)
        gate=Image.open(io.BytesIO(verified_master())).convert('RGB')
        # Preserve every pixel of the approved master; downscale proportionally, no crop.
        y=int(end+h*.108);lim=int(h*.90-y)
        if lim<100:raise HTTPException(422,'Creative headline too long for image')
        rendered=ImageOps.contain(gate,(int(w*.89),lim),Image.Resampling.LANCZOS)
        x=(w-rendered.width)//2
        im.paste(rendered,(int(x),y+max(0,(lim-rendered.height)//2)))
        d=ImageDraw.Draw(im)
        d.text((w*.056,h*.889),'ILLUSTRATIVE ARCHITECTURAL VISUAL · UNALTERED MASTER',
               font=font(min(w*.010,h*.018)),fill=INK)
        footer(d,w,h,INK)
    elif option==2:
        brand(d,w,h,WHITE)
        start=h*.15 if vertical else h*.17
        fs=min(w*.056,h*.071) if vertical else min(w*.043,h*.078)
        end=multiline(d,title,(w*.055,start),fs,w*.88,WHITE,maxlines=3 if vertical else 2)
        d.text((w*.058,end+h*.016),subtitle.upper(),font=font(min(w*.019,h*.028),True),fill='#ffb17a')
        r=min(w,h)*(.080 if vertical else .088)
        if vertical:
            yy=[h*.48,h*.66,h*.84];xx=[w*.52]*3
        else:
            yy=[h*.69]*3;xx=[w*.22,w*.50,w*.78]
        for k,(cx,cy) in enumerate(zip(xx,yy)):
            d.ellipse((cx-r,cy-r,cx+r,cy+r),fill='#2e6580',outline='#8bc2b0',width=4)
            if k==0:
                for t in range(3):
                    a=cx-r*.55+t*r*.4
                    d.rectangle((a,cy-r*.35,a+r*.29,cy+r*.36),fill='#ffb879')
            elif k==1:
                for t in range(8):
                    a=t*math.pi/4
                    d.line((cx,cy,cx+math.cos(a)*r*.57,cy+math.sin(a)*r*.57),
                           fill='#ffb879',width=max(4,int(w*.005)))
                d.ellipse((cx-r*.24,cy-r*.24,cx+r*.24,cy+r*.24),fill=CREAM)
            else:
                d.rectangle((cx-r*.55,cy-r*.23,cx+r*.36,cy+r*.25),fill='#ffb879')
                for a in (-.33,.18):
                    d.ellipse((cx+a*r-r*.13,cy+r*.18,cx+a*r+r*.13,cy+r*.44),fill=INK)
            label=['SUPPLY','OPERATIONS','DISPATCH'][k]
            f=font(min(w*.018,h*.030),True);width=d.textbbox((0,0),label,font=f)[2]
            d.text((cx-width/2,cy+r+9),label,font=f,fill=WHITE)
            if k<2:
                nx,ny=xx[k+1],yy[k+1]
                if vertical:d.line((cx,cy+r+28,nx,ny-r-28),fill=ORANGE,width=6)
                else:d.line((cx+r+22,cy,nx-r-22,ny),fill=ORANGE,width=6)
        d.text((w*.055,h*.884),'ILLUSTRATIVE BUSINESS WORKFLOW · NOT A SITE PLAN',
               font=font(min(w*.011,h*.017)),fill='#d0e5df')
        footer(d,w,h,WHITE)
    else:
        im=Image.new('RGB',(w,h),'#e8ece7')
        d=ImageDraw.Draw(im)
        d.rectangle((0,0,w*.30,h),fill='#194637')
        for j in range(13):d.line((w*.04,j*h/12,w*.26,j*h/12),fill='#396b55',width=1)
        sy=h*.11
        for row in ['PLAN','SPACE','GROW']:
            d.text((w*.045,sy),row,font=font(min(w*.034,h*.071),True),fill=WHITE)
            sy+=min(w*.060,h*.115)
        x=w*.355;start=h*.145 if vertical else h*.19
        fs=min(w*.041,h*.071) if vertical else min(w*.035,h*.080)
        end=multiline(d,title,(x,start),fs,w*.59,INK,maxlines=3)
        d.line((x,end+h*.019,w*.92,end+h*.019),fill=ORANGE,width=5)
        entries=[('01','BUSINESS TYPE','Manufacturing · Warehousing · Logistics'),
                 ('02','OPERATIONAL NEED','Understand the space and access required'),
                 ('03','NEXT PHASE','Plan capacity before choosing the plot')]
        first=max(end+h*.065,h*.37 if vertical else h*.48)
        step=(h*.86-first)/3
        for j,(num,label,explain) in enumerate(entries):
            y=first+j*step
            d.ellipse((x,y,x+min(w*.062,h*.070),y+min(w*.062,h*.070)),
                      outline=ORANGE,width=max(3,int(w*.0025)))
            d.text((x+min(w*.009,h*.013),y+min(w*.010,h*.011)),num,
                   font=font(min(w*.020,h*.031),True),fill=INK)
            tx=x+min(w*.08,h*.11)
            d.text((tx,y),label,font=font(min(w*.020,h*.035),True),fill=INK)
            d.text((tx,y+min(h*.055,w*.031)),explain,font=font(min(w*.011,h*.018)),fill='#426051')
        # Split-tone footer: white contact on dark green bar, dark website on cream.
        d.line((w*.05,h*.92,w*.95,h*.92),fill='#557666',width=2)
        d.text((w*.05,h*.949),'+91 74500 08999',font=font(min(w*.016,h*.025),True),fill=WHITE)
        website='lakhotiaindustrialcomplex.com';f=font(min(w*.015,h*.024),True)
        tw=d.textbbox((0,0),website,font=f)[2]
        d.text((w*.946-tw,h*.949),website,font=f,fill=INK)
    out=io.BytesIO()
    im.save(out,format='PNG',optimize=True)
    return out.getvalue()

def send(png,platform,option):
    return Response(png,media_type='image/png',headers={
        'Content-Disposition':f'attachment; filename="lakhotia-{platform.lower()}-concept-{option}.png"',
        'Cache-Control':'private, no-store'})

@router.get('/api/social-posts/{platform}/{option}.png')
def platform_post(platform:str,option:int):
    director_required()
    return send(image_bytes(option,platform),platform,option)

@router.get('/api/social-posts/ai/{batch_id}/{platform}/{option}.png')
def ai_platform_post(batch_id:str,platform:str,option:int):
    director_required()
    batch=batch_detail(batch_id)
    if option not in (1,2,3):raise HTTPException(404,'Invalid concept')
    candidate=batch['candidates'][option-1]
    return send(image_bytes(option,platform,candidate['headline'],candidate['subheadline']),platform,option)

@router.get('/api/social-posts/preview/{platform}/{option}.png')
def preview_platform_post(platform:str,option:int):
    return Response(image_bytes(option,platform),media_type='image/png',
                    headers={'Cache-Control':'private, max-age=60'})

@router.get('/api/social-posts/ai-preview/{batch_id}/{platform}/{option}.png')
def preview_ai_platform_post(batch_id:str,platform:str,option:int):
    data=batch_detail(batch_id)
    if option not in (1,2,3):raise HTTPException(404,'Invalid option')
    c=data['candidates'][option-1]
    return Response(image_bytes(option,platform,c['headline'],c['subheadline']),
                    media_type='image/png',headers={'Cache-Control':'private, max-age=60'})
