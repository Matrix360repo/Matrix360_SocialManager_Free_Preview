"""Execute the Director-authorized Oct 17 live production generation once.

Invoked at app startup after explicit Render opt-in. Records source outcome
without exposing secrets, and uses the same production media APIs as UI users.
"""
import os,threading
from security_roles import activate_actor,clear_actor

RUN_TAG='matrix360_p0_indian_sme_client_review_20261017'
BRIEF=("Create three authentic India-specific B2B creatives and 15-second motion reels "
"for SME/MSME light manufacturers, local small factories and growing modest "
"warehousing/logistics units near Howrah. ARCHITECTURE: use ONLY the exact "
"approved Lakhotia gate, unchanged; do not invent buildings. HUMAN OPERATIONS: "
"one or two clearly Indian local professionals, natural clothing or workwear, "
"small-workshop scale, realistic anatomy and lighting, not stock-style giant "
"factory imagery. UTILITIES & TECHNOLOGY: people-free real-world affordable "
"controls and gauges suitable for MSMEs; clearly illustrative, NOT existing "
"Lakhotia facilities. Distinct storytelling, kinetic typography, instrumental "
"music and intelligible short voiceover. CTA free industrial planning "
"consultation, +91 74500 08999. Omit all acreage claims and unsupported "
"claims of installed or completed facilities. "+RUN_TAG)

def archive_video(batch_id):
    try:
        from production_video_import import import_reel
        state=import_reel(batch_id)
        print('MATRIX360_LIVE_REEL_IMPORT result='+state,flush=True)
    except Exception as exc:
        print('MATRIX360_LIVE_REEL_IMPORT result=failed reason='+type(exc).__name__,flush=True)

def run():
    actor=activate_actor('Director')
    try:
        import durable_campaign_store as store
        from director_ai_studio import create_ai_batch
        if not store.is_configured():
            print('MATRIX360_LIVE_GENERATION result=private_storage_unavailable',flush=True)
            return
        batches=store.list_batches()
        matched=[x for x in batches if RUN_TAG in str(x.get('brief',''))]
        if matched:
            batch_id=str(matched[0]['id'])
            print('MATRIX360_LIVE_GENERATION result=already_registered batch='+batch_id,flush=True)
            archive_video(batch_id)
            return
        print('MATRIX360_LIVE_GENERATION result=starting_real_provider_requests',flush=True)
        batch=create_ai_batch(BRIEF,'Manufacturing businesses','Consultation enquiries','Instagram','openai')
        print('MATRIX360_LIVE_GENERATION result=three_posts_three_reels_created batch='+str(batch['id']),flush=True)
        archive_video(str(batch['id']))
    except Exception as exc:
        detail=getattr(exc,'detail',None)
        # Avoid printing provider-provided errors, headers or secret material.
        sanitized=str(detail)[:120] if isinstance(detail,str) else type(exc).__name__
        print('MATRIX360_LIVE_GENERATION result=failed reason='+sanitized,flush=True)
    finally:clear_actor(actor)

def kickoff():
    if os.getenv('MATRIX_PRODUCTION_GENERATE_ONCE','')!=RUN_TAG:
        return
    threading.Thread(target=run,daemon=True,name='director-authorized-live-generation').start()
