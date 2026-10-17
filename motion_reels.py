"""Verified motion-graphics MP4s: animated frames, voiceover and original music.

Uses already-produced private photos / exact locked original gate. Every output is
individually rendered by FFmpeg, ffprobed and rejected if audio/video is missing.
Never creates video artifacts by renaming PNGs or simulating provider success.
"""
import io
import json
import math
import os
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
GREEN=(9,42,36)
ORANGE=(241,114,61)
CREAM=(255,249,237)

class MotionRenderError(RuntimeError):
    pass

def font(size,bold=False):
    return ImageFont.truetype(BOLD if bold else FONT,int(size))

def fit_text(draw,text,max_width,size,max_lines=3):
    words=" ".join(str(text).split()).split(" ")
    f=font(size,True)
    result=[];line=""
    for word in words:
        trial=(line+" "+word).strip()
        if line and draw.textbbox((0,0),trial,font=f)[2]>max_width:
            result.append(line);line=word
        else:line=trial
    if line:result.append(line)
    return result[:max_lines]

def ease_out(x):
    x=max(0.,min(1.,x))
    return 1-(1-x)**3

def create_original_soundtrack(target,duration=15,rate=22050):
    """Synthesised original ambient chord bed, not a mislabeled stock track."""
    frequencies=(196.,261.63,329.63,392.)
    total=int(duration*rate)
    with wave.open(str(target),"wb") as audio:
        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(rate)
        chunk=bytearray()
        for i in range(total):
            t=i/rate
            note=frequencies[min(3,int(t/(duration/4)))]
            phase=t%0.30/0.30
            envelope=min(1.,t/.7,(duration-t)/1.1)
            tremolo=.75+.25*math.sin(2*math.pi*.25*t)
            value=(math.sin(2*math.pi*note*t)*.34+
                   math.sin(2*math.pi*(note*1.5)*t)*.13+
                   math.sin(2*math.pi*(note*.5)*t)*.32)
            sample=max(-1.,min(1.,value*envelope*tremolo*.28))
            chunk.extend(struct.pack("<h",int(sample*32767)))
            if len(chunk)>65536:
                audio.writeframesraw(chunk);chunk.clear()
        if chunk:audio.writeframesraw(chunk)

def base_plate(photo_bytes,option,width,height):
    try:
        with Image.open(io.BytesIO(photo_bytes)) as raw:
            raw.load()
            source=raw.convert("RGB")
            canvas=Image.new("RGB",(width,height),GREEN)
            if option==1:
                # The approved architectural original is never cropped or modified:
                # its pixels are only proportionately scaled into an inset.
                target=ImageOps.contain(source,(int(width*.94),int(height*.59)),
                    method=Image.Resampling.LANCZOS)
                canvas.paste(target,((width-target.width)//2,int(height*.17)))
            else:
                canvas=ImageOps.fit(source,(width,height),
                    method=Image.Resampling.LANCZOS,centering=(.5,.42))
            return canvas
    except Exception as exc:
        raise MotionRenderError("Source image is not decodable") from exc

def overlay_frame(frame,t,duration,option,reel,width,height):
    """Real motion graphics: per-frame kinetic text + dynamic vector layers."""
    image=Image.new("RGBA",(width,height),(0,0,0,0))
    d=ImageDraw.Draw(image,"RGBA")
    # Photographic tint and gradient darkening make lettering readable.
    for y in range(0,height,5):
        shade=int(65+140*(y/height))
        d.rectangle((0,y,width,y+5),fill=(0,27,22,min(215,shade)))
    bar=int(width*.045)
    d.rounded_rectangle((bar,int(height*.035),int(width*.955),int(height*.093)),
                        radius=14,fill=(5,39,32,190))
    d.text((int(width*.07),int(height*.048)),"LAKHOTIA INDUSTRIAL COMPLEX",
           font=font(max(16,width*.025),True),fill=CREAM)
    # Moving architectural guide lines / graphic threads. Motion is in the
    # compositing layers, not merely a photo panning across the frame.
    speed=t*width*.13
    for j in range(6):
        x=int((j*width*.27+speed)%(width*1.6)-width*.25)
        y=int(height*(.18+.057*j))
        d.line([(x,y),(x+width*.21,y-height*.028)],fill=(*ORANGE,65+j*14),
               width=max(2,int(width*.003)))
    orbit=t*2.5
    cx=width*(.78+.09*math.sin(orbit*.45))
    cy=height*(.43+.07*math.cos(orbit*.4))
    rad=width*.105
    d.arc((int(cx-rad),int(cy-rad),int(cx+rad),int(cy+rad)),
          start=int((t*70)%360),end=int((t*70+260)%360),
          fill=(*ORANGE,185),width=max(3,width//115))
    # The scene changes every five seconds. Each scene has moving title,
    # animated underline and its own imagery-independent kinetic layout.
    scene=min(2,int(t/(duration/3)))
    within=t%(duration/3)
    enter=ease_out(within/.8)
    exit_pos=ease_out(max(0.,within-(duration/3-0.65))/.65)
    offset=int((-width*.80)*(1-enter)+(width*.70)*exit_pos)
    title=str(reel.get("headline","Industrial planning")) if scene==0 else (
       "PLANNED FOR BUSINESS" if scene==1 else "DISCUSS YOUR LAND REQUIREMENT")
    detail=(
       "ARCHITECTURE & INFRASTRUCTURE" if option==1 else
       "PEOPLE & OPERATIONS" if option==2 else
       "UTILITIES & TECHNOLOGY · ILLUSTRATIVE")
    if scene==1:
        detail="MANUFACTURING  /  WAREHOUSING  /  LOGISTICS"
    if scene==2:detail="+91 74500 08999   |   lakhotiaindustrialcomplex.com"
    panel_y=int(height*(.74 if scene!=1 else .67))
    d.rounded_rectangle((int(width*.045)+offset,panel_y,
                         int(width*.96)+offset,panel_y+int(height*.185)),
                         radius=17,fill=(3,39,32,210))
    tx=int(width*.08)+offset
    d.text((tx,panel_y+int(height*.025)),
           "0"+str(scene+1)+"  /  MOTION STORY",font=font(width*.018,True),fill=(*ORANGE,255))
    title_y=panel_y+int(height*.062)
    for line in fit_text(d,title,int(width*.82),max(26,int(width*.048)),2):
        d.text((tx,title_y),line,font=font(width*.048,True),fill=CREAM)
        title_y+=int(height*.047)
    d.text((tx,min(title_y+int(height*.017),panel_y+int(height*.158))),
           detail,font=font(max(11,width*.018),True),fill=(245,191,146,255))
    d.rounded_rectangle((int(width*.065),int(height*.955),
                         int(width*.93),int(height*.962)),radius=3,fill=(255,255,255,65))
    d.rounded_rectangle((int(width*.065),int(height*.955),
                         int(width*.065+(width*.865)*min(1.,(t+.06)/duration)),
                         int(height*.962)),radius=3,fill=(*ORANGE,255))
    if option!=1:
        d.text((int(width*.065),int(height*.122)),
          "ILLUSTRATIVE INDUSTRY VISUAL · NOT LAKHOTIA SITE FOOTAGE",
          font=font(max(10,width*.013),True),fill=CREAM)
    else:
        d.text((int(width*.065),int(height*.122)),
          "OFFICIAL APPROVED GATE · ARCHITECTURE UNCHANGED",
          font=font(max(10,width*.013),True),fill=CREAM)
    return image

def voice_script(reel):
    title=" ".join(str(reel.get("headline","Industrial planning")).split())[:95]
    return (title+". Industrial land planning for manufacturing, warehousing and "
            "logistics in Howrah. Discuss your requirements with Lakhotia Industrial Complex.")

def synth_voice(client,reel):
    try:
        response=client.audio.speech.create(
            model=os.getenv("MATRIX_TTS_MODEL","tts-1"),
            voice=os.getenv("MATRIX_TTS_VOICE","nova"),
            input=voice_script(reel),response_format="mp3")
        audio=response.read()
    except Exception as exc:
        raise MotionRenderError("Voiceover provider request failed: "+type(exc).__name__) from None
    # Decode real provider audio; valid MP3 files have several frame headers.
    # The previous two-byte comparison rejected playable output.
    if len(audio)<1500:
        raise MotionRenderError("Voiceover provider returned empty audio")
    with tempfile.TemporaryDirectory(prefix="matrix360-voice-check-") as tmp:
        sample=Path(tmp)/"voice.mp3"
        sample.write_bytes(audio)
        result=subprocess.run(["ffprobe","-v","error","-show_entries",
             "stream=codec_type:format=duration","-of","json",str(sample)],
             capture_output=True,text=True,timeout=25)
        if result.returncode:
            raise MotionRenderError("Voiceover provider returned undecodable audio")
        try:
            info=json.loads(result.stdout)
            streams={x.get("codec_type") for x in info.get("streams",[])}
            seconds=float(info.get("format",{}).get("duration") or 0)
        except (TypeError,ValueError):
            raise MotionRenderError("Voiceover audio metadata invalid") from None
        if "audio" not in streams or seconds<1:
            raise MotionRenderError("Voiceover lacks playable speech audio")
    return audio

def probe_video(path,min_duration=10):
    if not shutil.which("ffprobe"):
        raise MotionRenderError("FFprobe is not installed in the render runtime")
    proc=subprocess.run(["ffprobe","-v","error","-show_entries",
       "stream=codec_type,codec_name:format=duration","-of","json",str(path)],
       capture_output=True,text=True,timeout=30)
    if proc.returncode:
        raise MotionRenderError("FFprobe rejected generated MP4")
    try:
        info=json.loads(proc.stdout)
        duration=float(info.get("format",{}).get("duration") or 0)
        stream_types={s.get("codec_type") for s in info.get("streams",[])}
    except (ValueError,TypeError):
        raise MotionRenderError("FFprobe returned invalid metadata") from None
    if duration<min_duration or not {"video","audio"}.issubset(stream_types):
        raise MotionRenderError("Generated reel lacks validated duration, video or audio stream")
    return {"duration":duration,"streams":sorted(stream_types)}

def render_reel(photo_bytes,option,reel,voice_mp3,duration=15,width=540,height=960,fps=18):
    if not shutil.which("ffmpeg"):
        raise MotionRenderError("FFmpeg is not installed")
    if not 1<=option<=3 or width<200 or height<300 or fps<5:
        raise MotionRenderError("Invalid reel settings")
    with tempfile.TemporaryDirectory(prefix="matrix360-motion-") as folder:
        root=Path(folder)
        base_plate(photo_bytes,option,width,height).save(root/"base.png")
        (root/"voice.mp3").write_bytes(voice_mp3)
        create_original_soundtrack(root/"music.wav",duration)
        total=int(duration*fps)
        for frame in range(total):
            t=frame/fps
            overlay_frame(frame,t,duration,option,reel,width,height).save(
                root/("overlay_%04d.png"%frame),compress_level=1)
        dest=root/"reel.mp4"
        cmd=["ffmpeg","-hide_banner","-nostdin","-loglevel","error","-y",
             "-threads","1","-filter_threads","1","-filter_complex_threads","1",
             "-loop","1","-framerate",str(fps),"-i",str(root/"base.png"),
             "-framerate",str(fps),"-i",str(root/"overlay_%04d.png"),
             "-i",str(root/"music.wav"),"-i",str(root/"voice.mp3"),
             "-filter_complex",
             "[0:v][1:v]overlay=shortest=1:format=auto,format=yuv420p[v];"
             "[2:a]volume=0.28[m];[m][3:a]amix=inputs=2:duration=first:dropout_transition=1[a]",
             "-map","[v]","-map","[a]","-t",str(duration),
             "-r",str(fps),"-c:v","libx264","-threads","1","-preset","ultrafast",
             "-crf","24","-pix_fmt","yuv420p","-c:a","aac","-b:a","128k",
             "-movflags","+faststart",str(dest)]
        try:
            done=subprocess.run(cmd,capture_output=True,text=True,timeout=max(180,int(duration*25)))
        except subprocess.TimeoutExpired:
            raise MotionRenderError("Motion renderer exceeded runtime limit") from None
        if done.returncode or not dest.exists():
            raise MotionRenderError("FFmpeg failed to encode motion graphics reel")
        probe_video(dest,min_duration=duration-1)
        return dest.read_bytes()
