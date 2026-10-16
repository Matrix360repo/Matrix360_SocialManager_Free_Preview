"""Matrix360 Lakhotia v1.4 brand-aligned proof renderer.

Three deliberate creative families: industrial opportunity, planning framework,
consultation. Uses unmodified official raster logo. No fabricated site images.
Designed for 1080 x 1350 feeds; drafts are not approved marketing assets.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from creative_renderer_v07 import _f, text_lines
from creative_renderer_v07 import C, N, O, W

SIZE=(1080,1350)
BASE=Path(__file__).resolve().parent
PHONE="+91 74500 08999"
WEB="lakhotiaindustrialcomplex.com"
ACCENT="#e95b20"

def _logo(im,x=58,y=38):
    src=BASE/"assets"/"lakhotia_group_logo_official.png"
    if not src.exists():raise FileNotFoundError("Official Lakhotia logo missing")
    with Image.open(src) as original:
        original=original.convert("RGBA")
        original.thumbnail((330,94),Image.Resampling.LANCZOS)
        # Retain the supplied pixels and their native background. Never recolor.
        im.paste(original,(x,y),original if original.mode=="RGBA" else None)

def _footer(im,dark=False,cta=None):
    d=ImageDraw.Draw(im)
    fg="white" if dark else C
    d.rectangle((0,1178,1080,1350),fill=C if dark else W)
    d.line((56,1180,1024,1180),fill=O,width=5)
    cta_text=(cta or "Discuss your industrial land requirement").strip()
    if len(cta_text)>65:cta_text="Discuss your industrial land requirement"
    text_lines(d,cta_text.upper(),60,1200,960,24,fg,True,1.12,2)
    d.text((60,1273),PHONE,font=_f(28,True),fill=fg)
    d.text((515,1279),WEB,font=_f(23),fill=fg)
    d.text((870,1323),"DRAFT • REVIEW",font=_f(13,True),fill="#a5c0b5" if dark else "#6a8b80")

def _heading(d,headline,y=230,size=61,lines=3,color=C):
    headline=(headline or "").strip()
    if not headline:raise ValueError("Headline is empty")
    # Reject layout overflow instead of truncating claims.
    font=_f(size,True)
    words=headline.split();wrapped=[];line=""
    for word in words:
        candidate=(line+" "+word).strip()
        if d.textbbox((0,0),candidate,font=font)[2]>960 and line:
            wrapped.append(line);line=word
        else:line=candidate
    if line:wrapped.append(line)
    if len(wrapped)>lines:raise ValueError("Headline too long for visual layout")
    for line in wrapped:
        d.text((58,y),line,font=font,fill=color)
        y+=int(size*1.19)
    return y

def _opportunity(c):
    im=Image.new("RGB",SIZE,W)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,13),fill=O)
    _logo(im)
    d.text((60,162),"LAKHOTIA INDUSTRIAL COMPLEX  /  HOWRAH",font=_f(24,True),fill=C)
    d.rectangle((60,207,145,216),fill=O)
    end=_heading(d,c.get("headline"),y=266,size=64,lines=3)
    d.text((60,552),"INDUSTRIAL LAND DEVELOPMENT",font=_f(26,True),fill=O)
    d.rectangle((60,610,1020,1006),fill=C)
    d.rectangle((60,610,73,1006),fill=O)
    labels=[
        ("LOCATION","Ranihati–Amta Road, Howrah"),
        ("CONNECTIVITY","Approx. 4 km from NH-16"),
        ("BUSINESS USE","Manufacturing / Warehousing / Logistics"),
        ("CAPACITY","1,000 bighas under development")
    ]
    for i,(title,body) in enumerate(labels):
        y=640+i*89
        d.text((102,y),title,font=_f(21,True),fill="#ffb28e")
        d.text((342,y-4),body,font=_f(25),fill="white")
        if i<3:d.line((100,y+51,980,y+51),fill="#41665e",width=2)
    d.text((63,1060),"2,500+ bighas planned expansion",font=_f(29,True),fill=C)
    d.text((64,1110),"Project facts • development and expansion are not completion claims",font=_f(19),fill=N)
    _footer(im,cta=c.get("cta"))
    return im

def _framework(c):
    im=Image.new("RGB",SIZE,"#f7f7f2")
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,14,1180),fill=O)
    _logo(im,60,40)
    d.text((62,169),"LAKHOTIA INDUSTRIAL COMPLEX",font=_f(24,True),fill=C)
    d.text((62,216),"PLAN YOUR NEXT INDUSTRIAL MOVE",font=_f(21,True),fill=O)
    _heading(d,c.get("headline"),y=275,size=58,lines=3)
    blocks=[
      ("01","LOCATION","Ranihati–Amta Road, Howrah"),
      ("02","OPERATIONS","Manufacturing · Warehousing · Logistics"),
      ("03","FUTURE PLANNING","2,500+ bighas planned expansion")
    ]
    for j,(num,label,detail) in enumerate(blocks):
        y=575+j*165
        d.rounded_rectangle((61,y,1019,y+141),radius=10,fill="white",outline="#cbdbd5",width=2)
        d.rectangle((61,y,73,y+141),fill=O)
        d.text((104,y+29),num,font=_f(47,True),fill=O)
        d.text((220,y+22),label,font=_f(32,True),fill=C)
        d.text((220,y+75),detail,font=_f(22),fill=N)
    d.text((66,1129),"1,000 bighas under development",font=_f(25,True),fill=C)
    _footer(im,cta=c.get("cta"))
    return im

def _consultation(c):
    im=Image.new("RGB",SIZE,W)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,13),fill=O)
    _logo(im)
    d.text((61,162),"LAKHOTIA INDUSTRIAL COMPLEX  /  ADVISORY",font=_f(23,True),fill=C)
    d.rectangle((59,214,1021,529),fill=C)
    d.rectangle((59,214,74,529),fill=O)
    # Reduced size protects line fit in dark panel.
    _heading(d,c.get("headline"),y=257,size=56,lines=3,color="white")
    d.text((60,558),"Industrial land decisions deserve informed planning.",font=_f(25),fill=N)
    imgpath=BASE/"assets"/"consultation_reference.png"
    with Image.open(imgpath) as original:
        original=original.convert("RGB")
        # Only historical consultation artwork, never positioned as actual project/site.
        top=int(original.height*0.64);bottom=int(original.height*0.91)
        crop=original.crop((0,top,original.width,bottom))
        crop=ImageOps.fit(crop,(960,440),method=Image.Resampling.LANCZOS)
        im.paste(crop,(60,622))
    d=ImageDraw.Draw(im)
    d.text((62,1092),"FREE EXPERT CONSULTATION  /  HOWRAH",font=_f(25,True),fill=C)
    d.text((62,1134),"Illustrative advisory reference, not an actual site photograph",font=_f(17),fill=N)
    _footer(im,dark=True,cta=c.get("cta"))
    return im

def render_card_v14(candidate,path,kind=0):
    # Stable three families, design_style override for revision selections.
    explicit=candidate.get("design_style")
    if explicit:
        family={"editorial_split":2,"bold_typography":0,"planning_infographic":1}.get(explicit)
        if family is None:raise ValueError("Unknown visual design direction")
    else:
        family=kind%3
    render=(_opportunity,_framework,_consultation)[family]
    im=render(candidate)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    im.save(path,"PNG")
    return path
