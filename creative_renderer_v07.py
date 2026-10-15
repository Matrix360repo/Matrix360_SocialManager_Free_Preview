"""Matrix360 v0.7: richer, offline, client-asset-aware proof renderer.
Replaces only render_card in existing engine; model/create/verify unchanged.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os
C='#063d34'; N='#112c45'; O='#e95b20'; W='#f9f8f4'; MUT='#566d70'

def _f(size,bold=False):
    from PIL import ImageFont
    from pathlib import Path
    import os
    paths = ([os.environ.get('WINDIR','C:/Windows')+'/Fonts/arialbd.ttf', os.environ.get('WINDIR','C:/Windows')+'/Fonts/segoeuib.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else [os.environ.get('WINDIR','C:/Windows')+'/Fonts/arial.ttf', os.environ.get('WINDIR','C:/Windows')+'/Fonts/segoeui.ttf','/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for p in paths:
        if Path(p).exists():
            try:return ImageFont.truetype(p,size)
            except OSError:pass
    return ImageFont.load_default()

def text_lines(draw,s,x,y,max_width,size=45,color=C,bold=False,spacing=1.24,max_lines=5):
    font=_f(size,bold); pieces=[]; line=''
    for word in str(s).split():
        candidate=(line+' '+word).strip()
        if draw.textbbox((0,0),candidate,font=font)[2]>max_width and line:
            pieces.append(line);line=word
        else:line=candidate
    if line:pieces.append(line)
    pieces=pieces[:max_lines]
    for line in pieces:
        draw.text((x,y),line,font=font,fill=color,stroke_width=0)
        y+=int(size*spacing)
    return y

def logo(im,base,x=56,y=45,limit=(340,94)):
    p=base/'assets'/'lakhotia_group_logo_official.png'
    if not p.exists():raise FileNotFoundError('Official Lakhotia logo missing')
    l=Image.open(p).convert('RGB');l.thumbnail(limit,Image.Resampling.LANCZOS)
    im.paste(l,(x,y))

def foot(im,dark=False,site=True):
    d=ImageDraw.Draw(im)
    d.rectangle((0,1200,1080,1350),fill=C if dark else W)
    if not dark:d.line((55,1200,1025,1200),fill='#c9d3cf',width=2)
    main='#ffffff' if dark else C
    d.text((60,1222),'DISCUSS YOUR INDUSTRIAL LAND REQUIREMENT',font=_f(28,True),fill=main)
    d.text((60,1272),'+91 74500 08999',font=_f(29,True),fill=main)
    d.text((565,1281),'lakhotiaindustrialcomplex.com',font=_f(22),fill=main)
    d.text((910,1324),'CONCEPT PROOF',font=_f(13,True),fill='#b8c8bf' if dark else '#78918b')

def card_one(c,base):
    im=Image.new('RGB',(1080,1350),W);d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,11),fill=O);logo(im,base)
    d.text((62,169),'INDUSTRIAL OPPORTUNITY',font=_f(23,True),fill=O)
    title=c.get('headline','Industrial growth starts with the right plan')
    yy=text_lines(d,title,60,219,938,65,C,True,1.13,3)
    d.text((62,yy+14),'Industrial land, planned around your business requirements.',font=_f(26),fill=N)
    # Reference photograph used only as photographic reference, crop excludes text/CTA.
    img=Image.open(base/'assets'/'consultation_reference.png').convert('RGB')
    crop=img.crop((0,290,img.width,446))
    crop=ImageOps.fit(crop,(960,515),method=Image.Resampling.LANCZOS,centering=(0.5,0.55))
    im.paste(crop,(60,610))
    d=ImageDraw.Draw(im)
    d.rectangle((60,1063,1020,1125),fill=C)
    d.text((83,1078),'PLAN  /  SET UP  /  GROW',font=_f(31,True),fill='white')
    d.text((62,1145),'Reference artwork • illustrative visual, not site photography',font=_f(19),fill=MUT)
    foot(im,dark=True);return im

def card_two(c,base):
    im=Image.new('RGB',(1080,1350),'#f3f4ee');d=ImageDraw.Draw(im)
    d.rectangle((0,0,18,1350),fill=O);logo(im,base,60,37)
    d.text((62,172),'THE BUSINESS DECISION FRAMEWORK',font=_f(24,True),fill=O)
    y=text_lines(d,c.get('headline','Plan your industrial expansion'),62,220,950,62,C,True,1.15,3)
    y=max(y+50,480)
    labels=[('01','LOCATION','Geography and connectivity'),('02','INFRASTRUCTURE','Movement, utilities and access'),('03','FUTURE CAPACITY','Plan for operational expansion')]
    for j,(num,title,subtitle) in enumerate(labels):
        top=y+j*182
        d.rounded_rectangle((61,top,1019,top+154),radius=14,fill='white',outline='#d0dcd4',width=2)
        d.rounded_rectangle((82,top+31,176,top+121),radius=8,fill=C)
        d.text((105,top+51),num,font=_f(38,True),fill='white')
        d.text((205,top+32),title,font=_f(35,True),fill=O if j==1 else C)
        d.text((205,top+88),subtitle,font=_f(27),fill=N)
    d.text((63,1146),'Lakhotia Industrial Complex  |  Howrah',font=_f(24,True),fill=C)
    foot(im,False);return im

def card_three(c,base):
    im=Image.new('RGB',(1080,1350),'#f8f9f7');d=ImageDraw.Draw(im)
    d.rectangle((0,0,1080,560),fill=C)
    logo(im,base,60,35)
    d.text((60,182),'PLAN  •  SET UP  •  GROW',font=_f(24,True),fill='#ffb08c')
    text_lines(d,c.get('headline','Expert guidance for businesses'),60,232,930,66,'white',True,1.14,3)
    d.text((63,494),'Industrial planning and free consultation',font=_f(27),fill='#ebf2ef')
    # Wide photo is the approved historic *consultation* creative, not an actual site photo.
    src=Image.open(base/'assets'/'consultation_reference.png').convert('RGB')
    src=src.crop((0,295,src.width,448))
    src=ImageOps.fit(src,(960,430),method=Image.Resampling.LANCZOS)
    im.paste(src,(60,595))
    d=ImageDraw.Draw(im)
    d.line((60,1074,1020,1074),fill=O,width=5)
    d.text((62,1100),'INDUSTRY EXPERTISE   •   PRACTICAL GUIDANCE',font=_f(25,True),fill=C)
    d.text((62,1146),'Visual reference supplied by the client',font=_f(19),fill=MUT)
    foot(im,False);return im

def render_card_v07(candidate,path,kind=0):
    base=Path(__file__).resolve().parent
    im=[card_one,card_two,card_three][kind%3](candidate,base)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    im.save(path,format='PNG')
    return path
