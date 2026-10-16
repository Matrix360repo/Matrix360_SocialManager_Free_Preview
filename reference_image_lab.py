"""Director-gated reference-guided image generation, internal evaluation only.

Never use output as verified site photography, never publish automatically.
Approved input assets are reused without changing their approval status.
"""
import base64
import io
import os
import uuid
from html import escape
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from PIL import Image

from brand_asset_studio import DIR, dbconn
from security_roles import director_required

router = APIRouter()
OUT = Path(__file__).resolve().parent / 'data' / 'image_lab'
MAX_OUTPUT_BYTES = 25 * 1024 * 1024
STYLE_BRIEF = (
    "Create ONE new photorealistic architectural marketing background inspired by "
    "the provided, Director-cleared industrial development reference image. "
    "Preserve the overall high-end, realistic architectural art direction but "
    "create a visibly different camera composition. Do not invent project-specific "
    "finished infrastructure or claim that this is a real photograph of the site. "
    "No writing, letters, numbers, logos, signage, watermarks, billboards, "
    "contact details or typographic layouts anywhere in the output. "
    "Leave calm negative space for subsequently composited exact brand copy. "
    "This image is an ILLUSTRATIVE CONCEPT ONLY. Subject: "
)

def approved_reference(asset_id: str) -> Path:
    try:
        ident = str(uuid.UUID(asset_id))
    except ValueError as exc:
        raise HTTPException(404, 'Invalid reference asset ID') from exc
    with dbconn() as db:
        row = db.execute('SELECT status FROM brand_assets WHERE id=?', (ident,)).fetchone()
    if not row:
        raise HTTPException(404, 'Reference image is not registered')
    if row[0] != 'approved_proof':
        raise HTTPException(403, 'Director must approve the source image for internal proofs')
    source = DIR / (ident + '.png')
    if not source.is_file():
        raise HTTPException(410, 'Reference was lost from ephemeral storage; re-upload')
    return source

def generate_reference_image(asset_id: str, subject: str, quality: str = 'low',
                             consent: str = '') -> dict:
    # Cost-bearing action: no automatic execution, operator invocation or scheduled batch.
    director_required()
    # ARCHITECTURE SAFETY STOP (2026-10-16):
    # Lakhotia_Gate_Master_Lock.md defines one immutable gate master. An image
    # edit model cannot guarantee that geometry, landscaping or site layout
    # will be preserved. Block the call BEFORE the paid provider request.
    # Re-enable only after an approved reference grid, region-lock masks and
    # evidence-based post-generation checks are implemented and reviewed.
    raise HTTPException(
        409,
        'Architectural image generation is suspended: the approved gate and '
        'site plan must be preserved exactly. Use unchanged approved artwork '
        'for compositions until reference-grid verification is available.'
    )
    if consent != 'one_paid_image':
        raise HTTPException(422, 'Director must explicitly authorize this paid image request')
    if quality not in ('low', 'medium'):
        raise HTTPException(422, 'Pilot only permits low/medium quality')
    if not 12 <= len(subject.strip()) <= 300:
        raise HTTPException(422, 'Describe the creative subject in 12–300 characters')
    source = approved_reference(asset_id)
    api_key = os.getenv('OPENAI_API_KEY', '').strip()
    if not api_key:
        raise HTTPException(503, 'Image generation unavailable: configure OPENAI_API_KEY')
    model = os.getenv('MATRIX_IMAGE_MODEL', 'gpt-image-2')
    if model not in ('gpt-image-2', 'gpt-image-1.5'):
        raise HTTPException(503, 'Unsupported image model configured')
    # Import only when executing an explicitly authorized paid operation.
    from openai import OpenAI
    try:
        client = OpenAI(api_key=api_key, timeout=110.0, max_retries=0)
        with source.open('rb') as image_file:
            result = client.images.edit(
                model=model, image=image_file,
                prompt=STYLE_BRIEF + subject.strip(),
                size='1024x1536', quality=quality, n=1,
            )
        encoded = result.data[0].b64_json
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) > MAX_OUTPUT_BYTES:
            raise ValueError('Generated image exceeded internal size cap')
        with Image.open(io.BytesIO(raw)) as img:
            img.verify()
        with Image.open(io.BytesIO(raw)) as img:
            if img.width < 512 or img.height < 512:
                raise ValueError('Generated image is unexpectedly small')
            clean = io.BytesIO()
            img.convert('RGB').save(clean, format='PNG')
        proof_id = str(uuid.uuid4())
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / (proof_id + '.png')).write_bytes(clean.getvalue())
    except Exception as exc:
        # Avoid exposing provider payloads, secrets, or internal traces.
        raise HTTPException(502, 'AI image generation failed; check provider access, model, credits and Render logs') from exc
    return {'id': proof_id, 'status': 'unapproved_internal_proof',
            'image_url': '/api/image-lab/proofs/' + proof_id,
            'reference_asset_id': asset_id, 'model': model,
            'warning': 'AI-generated illustrative concept; not a verified site photograph or publishing approval'}

@router.post('/api/image-lab/generate')
def generate(asset_id: str = Form(...), subject: str = Form(...),
             quality: str = Form('low'), consent: str = Form('')):
    return generate_reference_image(asset_id, subject, quality, consent)

@router.get('/api/image-lab/proofs/{proof_id}')
def view_proof(proof_id: str):
    try:
        proof_id = str(uuid.UUID(proof_id))
    except ValueError as exc:
        raise HTTPException(404, 'Unknown generated proof') from exc
    source = OUT / (proof_id + '.png')
    if not source.is_file():
        raise HTTPException(404, 'Proof expired on ephemeral deployment')
    return FileResponse(source, media_type='image/png',
                        headers={'Cache-Control': 'no-store',
                                 'X-Matrix360-Image-Status': 'unapproved-internal-proof'})

@router.get('/image-lab', response_class=HTMLResponse)
def lab_page():
    director_required()
    with dbconn() as db:
        rows = db.execute("SELECT id, filename FROM brand_assets WHERE status='approved_proof' ORDER BY created DESC LIMIT 30").fetchall()
    options = ''.join('<option value="'+escape(row[0],quote=True)+'">'+escape(row[1])+' · '+escape(row[0])+'</option>' for row in rows)
    return HTMLResponse('''<!doctype html><html><head><meta charset="utf-8"><title>Matrix360 Image Lab</title></head>
<body style="font:16px system-ui;max-width:730px;margin:40px auto;padding:15px;background:#f8faf8;color:#123e33">
<a href="/brand-studio">← Brand Studio</a><h1>Reference-Guided Image Lab</h1>
<p><strong>Director-only · Paid API call · One image per submission · Internal evaluation</strong></p>
<p>Approved backgrounds influence new imagery. Generated visuals contain no trustworthy project signs, claims or copy; exact brand layers must be added in a later step.</p>
<form action="/api/image-lab/generate" method="post" style="display:grid;gap:16px">
<label>Director-approved reference image<select name="asset_id" required style="display:block;width:100%;padding:10px">'''+options+'''</select></label>
<label>Creative subject<textarea name="subject" required minlength="12" maxlength="300" rows="4" style="display:block;width:100%">Wide-angle conceptual entrance to a premium industrial development in Howrah, realistic daylight, clean gate, landscaped verge, industrial sheds in distance.</textarea></label>
<label>Proof quality<select name="quality"><option value="low">Low (least expensive test)</option><option value="medium">Medium</option></select></label>
<label><input type="checkbox" name="consent" value="one_paid_image" required> Director authorizes ONE paid API image request for internal proof.</label>
<button style="padding:12px">Generate single AI reference-guided background</button>
</form><p><small>Raw JSON response contains the generated image_url. Do not interpret these outputs as actual site photographs. No autopublishing.</small></p>
</body></html>''')
