"""Director production media workspace. No fixed campaign concepts or dummy art."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from security_roles import current_actor

router=APIRouter()

@router.get('/director-demo',response_class=HTMLResponse)
@router.get('/production-studio',response_class=HTMLResponse)
def production_studio():
    role='Director' if current_actor()=='Director' else 'Read-only operator'
    return HTMLResponse(r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Matrix 360 — Production AI Studio</title>
<style>
:root{font-family:Inter,system-ui,-apple-system,sans-serif;color:#17372e;background:#f5f6f2}
*{box-sizing:border-box}body{margin:0}header{background:#11362f;color:white;padding:22px max(22px,calc((100vw - 1340px)/2));display:flex;align-items:center;justify-content:space-between}
header strong{font-size:23px}header small{color:#b6cebf;font-size:11px;letter-spacing:1.6px}
main{max-width:1340px;margin:32px auto 80px;padding:0 24px}h1{font-size:clamp(32px,4vw,54px);letter-spacing:-1.6px;margin:7px 0 8px}
.kicker{font-size:11px;color:#bc6f44;letter-spacing:2px;font-weight:800}
.lead{color:#68796e;max-width:780px}h2{font-size:24px;letter-spacing:-.5px;margin:0 0 12px}
.panel{background:white;padding:24px;border:1px solid #dce3dc;border-radius:14px;margin:22px 0}
label{display:flex;flex-direction:column;gap:8px;font-size:12px;font-weight:750}
textarea,select{border:1px solid #cad8cc;background:#fbfcfa;padding:12px;border-radius:8px;color:#183d33;font:inherit}
textarea{width:100%;min-height:120px;resize:vertical}.grid4{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:16px 0}
button,.button{font:inherit;cursor:pointer;padding:11px 16px;border:0;border-radius:8px;background:#e97940;color:#fff;font-weight:750;font-size:12px;text-decoration:none;display:inline-block}
button:disabled{opacity:.55;cursor:not-allowed}.button.subtle,button.subtle{background:#e8eee9;color:#18493b}
.status{padding:12px 15px;background:#edf2ed;border-radius:7px;color:#38594b;font-size:12px;margin-top:12px}
.output{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin-top:19px}
.card{border:1px solid #d5e0d7;border-radius:11px;background:#fff;overflow:hidden}
.card-body{padding:18px}.card h3{font-size:20px;line-height:1.2;margin:10px 0}
.card p{font-size:12px;color:#607267;line-height:1.55}
.visual{background:#edf2ec;min-height:80px}.visual img{width:100%;height:auto;display:block}
video{width:100%;height:auto;display:block;background:#0e241d;aspect-ratio:9/16}
.pill{display:inline-block;border-radius:30px;background:#e9e8dd;padding:4px 9px;font-size:10px;font-weight:800}
.actions{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.actions button{padding:8px 10px}
select{max-width:100%}.downloads{display:flex;flex-wrap:wrap;gap:7px;margin-top:14px}
.downloads a{font-size:10px;background:#164c3e;color:#fff;padding:8px;border-radius:6px;text-decoration:none}
.notes{font-size:11px;color:#687b6e;margin-top:8px}.error{color:#a33929}
hr{border:0;border-top:1px solid #e5ebe5;margin:25px 0}
@media(max-width:900px){.output{grid-template-columns:1fr}.grid4{grid-template-columns:1fr 1fr}}
@media(max-width:530px){.grid4{grid-template-columns:1fr}header{padding:18px}}
</style></head><body><header><div><strong>MATRIX 360</strong><br><small>PRODUCTION CREATIVE STUDIO · LAKHOTIA</small></div><small>''' + role + r''' · controlled publishing</small></header>
<main><div class="kicker">LIVE AI GENERATION / PRIVATE SUPABASE STORAGE</div>
<h1>Creative production, not placeholders.</h1>
<p class="lead">Generate three distinct photographic social concepts and three genuine motion-video reel concepts from your brief. Images and MP4s appear only after the respective AI provider has completed rendering.</p>
<section class="panel"><h2>New campaign brief</h2>
<form id="generate">
<label>What should this campaign communicate?
<textarea name="brief" required minlength="15" maxlength="900" placeholder="Describe the business objective, audience, proof points and tone."></textarea></label>
<div class="grid4">
<label>Audience<select name="audience"><option>Manufacturing businesses</option><option>Warehousing operators</option><option>Logistics and 3PL</option><option>Industrial investors and occupiers</option></select></label>
<label>Objective<select name="objective"><option>Consultation enquiries</option><option>Awareness</option><option>Thought leadership</option></select></label>
<label>Primary channel<select name="platform"><option>Instagram</option><option>Facebook</option><option>LinkedIn</option><option>X-Twitter</option></select></label>
<label>Text model<select name="provider"><option value="openai">OpenAI</option><option value="groq">Groq</option></select></label>
</div><button id="start" type="submit">Generate 3 posts + 3 motion reels</button>
</form><div id="feedback" class="status">Production assets are created on demand using live AI providers; usage is billable. No external publishing.</div></section>
<section id="output" hidden><div class="panel"><div class="kicker">SOCIAL PLATFORM EXPORTS</div><h2>Three generated post concepts</h2>
<label>Preview format<select id="channel"><option>Instagram</option><option>Facebook</option><option>LinkedIn</option><option>X-Twitter</option></select></label>
<div id="posts" class="output"></div></div>
<div class="panel"><div class="kicker">LIVE MOTION RENDERING</div><h2>Three AI-generated reels</h2>
<p class="lead">Reels use a genuine motion-video model. No storyboard-only output or animated still posters. Rendering may take several minutes and requires provider video entitlement.</p>
<div id="reels" class="output"></div></div></section>
<section class="panel"><h2>Recent durable campaigns</h2><div id="history" class="notes">Loading saved campaigns...</div>
<p class="notes">All approval actions are Director-only and audited. AI output is unapproved until reviewed. External social publishing remains disabled.</p></section>
</main>
<script>
const $=id=>document.getElementById(id);let current=null,ticker=null;
const enc=s=>encodeURIComponent(s);
function elt(tag,text,cls){let el=document.createElement(tag);if(text!==undefined)el.textContent=String(text);if(cls)el.className=cls;return el}
function info(message,bad=false){$('feedback').textContent=message;$('feedback').className='status'+(bad?' error':'')}
async function json(url,options){let res=await fetch(url,options),data;
try{data=await res.json()}catch{throw Error('Server returned '+res.status)}
if(!res.ok)throw Error(typeof data.detail==='string'?data.detail:'Request failed ('+res.status+')');
return data}
function button(parent,text,fn,cls){let b=elt('button',text,cls);b.type='button';b.addEventListener('click',fn);parent.append(b);return b}
function link(parent,text,url,download=false){const a=elt('a',text);a.href=url;a.target='_blank';a.rel='noopener';if(download)a.download='';parent.append(a)}
const names=['Instagram','Facebook','LinkedIn','X-Twitter'];
function postUrl(option,channel){return '/api/production-media/'+enc(current.id)+'/'+enc(channel)+'/'+option+'.png'}
function reelUrl(option){return '/api/production-media/'+enc(current.id)+'/reel/'+option+'/video.mp4'}
async function review(option,kind,decision){
 const note=decision==='revision_requested'?prompt('Required revision (mandatory):'):(decision==='rejected'?prompt('Rejection reason (optional):',''):'');
 if(note===null)return;
 try{const body=new URLSearchParams({decision,note:note||''});
 let endpoint=kind==='Reel'?'/api/director-demo/ai/batches/'+enc(current.id)+'/reels/'+option+'/decision':
 '/api/director-demo/ai/batches/'+enc(current.id)+'/'+option+'/decision';
 let result=await json(endpoint,{method:'POST',body});
 info(kind+' '+option+': '+result.decision+'. Stored securely; publishing disabled.');
 await showBatch(current.id)
 }catch(err){info('Review not saved: '+err.message,true)}
}
function reviewActions(card,option,kind,check,decision){
 const box=elt('div',undefined,'actions');
 button(box,'Approve',()=>review(option,kind,'approved'));
 button(box,'Reject',()=>review(option,kind,'rejected'),'subtle');
 button(box,'Request revision',()=>review(option,kind,'revision_requested'),'subtle');
 card.append(box);
 const msg=elt('div',(decision?'Director: '+decision+' · ':'')+(check.passed?'Claims screen passed':'Claims review required: '+(check.issues||[]).join('; ')),'notes'+(check.passed?'':' error'));
 card.append(msg)
}
function displayPosts(status){
 const node=$('posts');node.replaceChildren();
 const channel=$('channel').value;
 (current.candidates||[]).forEach((item,i)=>{
   const idx=i+1,s=status.image[i]||{},c=current.checks[i]||{passed:false,issues:['Unscreened']};
   const card=elt('article',undefined,'card'),visual=elt('div',undefined,'visual');
   if(s.status==='completed'){
     const img=elt('img');img.src=postUrl(idx,channel);img.alt='AI photographic composition '+idx+' for '+channel;
     img.addEventListener('error',()=>{visual.replaceChildren(elt('div','Image unavailable from private storage','status error'))});
     visual.append(img)
   }else{visual.append(elt('div','Image render: '+(s.status||'queued')+(s.error_message?' — '+s.error_message:''),'status'+(s.status==='failed'?' error':'')))}
   card.append(visual);
   const body=elt('div',undefined,'card-body');
   body.append(elt('span','POST 0'+idx+' · '+(item.pillar||''),'pill'),elt('h3',item.headline),elt('p',item.caption));
   if(s.status==='completed'){const links=elt('div',undefined,'downloads');
     names.forEach(ch=>link(links,ch+' PNG',postUrl(idx,ch),true));body.append(links)}
   reviewActions(body,idx,'Post',c,(current.reviews||{})[idx]?.decision);
   card.append(body);node.append(card)
 })
}
function displayReels(status){
 const node=$('reels');node.replaceChildren();
 (current.reels||[]).forEach((reel,i)=>{
  const idx=i+1,s=status.video[i]||{},card=elt('article',undefined,'card');
  if(s.status==='completed'){
   const v=elt('video');v.controls=true;v.preload='metadata';v.playsInline=true;v.src=reelUrl(idx);card.append(v)
  }else card.append(elt('div','Video rendering: '+(s.status||'queued')+
    (s.error_message?' — '+s.error_message:''),'status'+(s.status==='failed'?' error':'')));
  const body=elt('div',undefined,'card-body');
  body.append(elt('span','REEL 0'+idx,'pill'),elt('h3',reel.headline),elt('p',reel.caption||''));
  if(s.status==='completed'){const links=elt('div',undefined,'downloads');link(links,'Play / download MP4',reelUrl(idx),true);body.append(links)}
  else if(s.status==='processing'&&s.provider_job_id){
    button(body,'Check video render',()=>refreshVideo(idx),'subtle');
  }
  reviewActions(body,idx,'Reel',current.checks[i]||{passed:false,issues:['Unscreened']},(current.reel_reviews||{})[idx]?.decision);
  card.append(body);node.append(card)
 })
}
async function refreshVideo(idx){
 try{await json('/api/production-media/'+enc(current.id)+'/reel/'+idx+'/refresh',{method:'POST'});await refresh()}
 catch(err){info('Video job: '+err.message,true)}
}
async function refresh(){
 if(!current)return;
 try{
  const status=await json('/api/production-media/'+enc(current.id)+'/status');
  displayPosts(status);displayReels(status);
  for(const video of status.video||[]){
   if(video.status==='processing'&&video.provider_job_id){
    await refreshVideoQuiet(video.option_no);
   }
  }
 }catch(err){info('Render status unavailable: '+err.message,true)}
}
async function refreshVideoQuiet(idx){
 try{await json('/api/production-media/'+enc(current.id)+'/reel/'+idx+'/refresh',{method:'POST'})}
 catch(err){console.warn('Video status unavailable',err.message)}
}
async function showBatch(id){
 try{current=await json('/api/director-demo/ai/batches/'+enc(id));
 if(!current.reels||current.reels.length!==3)throw Error('This batch predates production video generation. Start a new brief.');
 $('output').hidden=false;await refresh()
 }catch(err){info('Unable to open campaign: '+err.message,true)}
}
$('channel').addEventListener('change',refresh);
$('generate').addEventListener('submit',async ev=>{
 ev.preventDefault();const submit=$('start');submit.disabled=true;info('Calling AI for three new post and motion-video concepts. Then production rendering begins...');
 try{const batch=await json('/api/director-demo/ai/generate',{method:'POST',body:new FormData($('generate'))});
 info('AI concepts generated from '+batch.provider+'. Real images and motion reels are rendering. Failed providers will show explicit errors.');
 await showBatch(batch.id);await history()
 }catch(err){info('Generation failed: '+err.message,true)}
 finally{submit.disabled=false}
});
async function history(){
 try{const data=await json('/api/director-demo/ai/batches'),box=$('history');box.replaceChildren();
 (data.batches||[]).forEach(b=>button(box,(b.created_utc||'').slice(0,16)+' · '+b.brief.slice(0,90),
 ()=>showBatch(b.id),'subtle'));
 if(!data.batches?.length)box.append(elt('span','No stored AI campaigns yet.'))}
 catch(err){$('history').textContent='History unavailable: '+err.message}
}
history();ticker=setInterval(async()=>{if(current)await refresh()},20000);
</script></body></html>''')
