"""Explicit, deterministic visual layout modes for human-reviewed creative revisions.
No claim that freeform feedback is AI-interpreted. Original renderer stays unchanged.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from creative_renderer_v07 import _f, text_lines, logo, foot, C, O, N, W, MUT

MODES=('editorial_split','bold_typography','planning_infographic')

def render(candidate,path,mode):
    if mode not in MODES: raise ValueError('Unknown visual direction')
    base=Path(__file__).resolve().parent
    im=Image.new('RGB',(1080,1350), W if mode!='bold_typography' else C)
    d=ImageDraw.Draw(im)
    headline=candidate['headline']; sub=candidate.get('subheadline',''); cta=candidate.get('cta','')
    if mode=='editorial_split':
        d.rectangle((0,0,1080,12),fill=O);logo(im,base,48,29,limit=(310,87))
        d.text((50,152),'STRATEGIC INDUSTRIAL EXPANSION',font=_f(22,True),fill=O)
        text_lines(d,headline,48,200,945,72,C,True,1.10,3)
        src=Image.open(base/'assets'/'consultation_reference.png').convert('RGB')
        crop=src.crop((0,290,src.width,446));crop=ImageOps.fit(crop,(530,600),method=Image.Resampling.LANCZOS)
        im.paste(crop,(550,490));d=ImageDraw.Draw(im)
        d.rectangle((0,490,550,600),fill=O)
        d.rectangle((0,600,550,1090),fill=C)
        d.text((48,517),'PLAN / EVALUATE / EXPAND',font=_f(25,True),fill='white')
        y=text_lines(d,sub,48,672,452,41,'white',True,1.30,5)
        d.text((48,min(y+64,990)),'HOWRAH, WEST BENGAL',font=_f(22,True),fill='#ffb08c')
        d.text((553,1110),'Illustrative reference artwork, not site photography',font=_f(17),fill=MUT)
        d.rectangle((48,1120,1024,1180),fill=O)
        text_lines(d,cta.upper(),66,1134,920,24,'white',True,1.05,2)
        foot(im,True)
    elif mode=='bold_typography':
        d.rectangle((0,0,1080,14),fill=O);logo(im,base,46,35,limit=(300,87))
        d.text((53,182),'BUSINESS GROWTH  /  HOWRAH',font=_f(26,True),fill='#ffb490')
        d.rectangle((51,252,125,262),fill=O)
        end=text_lines(d,headline.upper(),52,319,975,98,'white',True,1.09,5)
        d.rectangle((50,max(835,end+40),1027,max(849,end+55)),fill=O)
        y=max(875,end+100)
        text_lines(d,sub,55,y,956,36,'#e8f2ef',False,1.23,3)
        d.rounded_rectangle((52,1085,1026,1177),radius=8,fill=O)
        text_lines(d,cta.upper(),74,1110,922,29,'white',True,1.05,2)
        foot(im,True)
    else:
        d.rectangle((0,0,1080,14),fill=O);logo(im,base,52,31,limit=(300,88))
        d.text((54,175),'INDUSTRIAL EXPANSION FRAMEWORK',font=_f(27,True),fill=O)
        end=text_lines(d,headline,54,232,968,65,C,True,1.15,3)
        d.text((57,min(end+15,486)),sub[:88],font=_f(25),fill=N)
        tiles=[('01','LOCATION','Connectivity and access'),('02','OPERATIONS','Manufacturing and logistics'),('03','SCALABILITY','Long-term expansion planning')]
        for ix,(num,lab,info) in enumerate(tiles):
            y=526+ix*187
            d.rounded_rectangle((52,y,1028,y+163),radius=19,fill='#e8efeb' if ix!=1 else C)
            fg='white' if ix==1 else C
            d.rounded_rectangle((73,y+30,164,y+133),radius=9,fill=O)
            d.text((90,y+60),num,font=_f(34,True),fill='white')
            d.text((187,y+28),lab,font=_f(41,True),fill=fg)
            d.text((187,y+94),info,font=_f(27),fill=fg)
        d.rectangle((53,1104,1027,1180),fill=O)
        text_lines(d,cta.upper(),75,1126,910,27,'white',True,1.08,2)
        foot(im,False)
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);im.save(path,format='PNG');return path
