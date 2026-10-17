"""Execute the Director-authorized Oct 17 live production generation once.

Invoked at app startup after explicit Render opt-in. Records source outcome
without exposing secrets, and uses the same production media APIs as UI users.
"""
import os,threading
from security_roles import activate_actor,clear_actor

RUN_TAG='matrix360_issue29_distinct_client_quality_live_v2'
BRIEF=("Develop a polished, factual B2B campaign for Lakhotia Industrial Complex, "
"Ranihati-Amta Road, Howrah. THREE nonoverlapping social post and motion-graphics "
"reel categories: first ARCHITECTURE & INFRASTRUCTURE using ONLY the exact "
"Director-approved gate reference without invented site structures or plans; "
"second HUMAN OPERATIONS with one or two naturally posed industrial professionals "
"in an illustrative generic industrial workplace (no duplicate faces or limbs); "
"third FACILITIES UTILITIES & TECHNOLOGY showing people-free generic "
"industrial monitoring instruments and controls, explicitly illustrative and NOT "
"installed Lakhotia utilities. Realistic images and distinct copy for each. "
"Highlight manufacturing, warehousing, logistics, industrial land planning and "
"free expert consultation with correct Lakhotia phone and website. "
"Do not claim ready infrastructure, operational power/water, installed "
"substations, regulatory certification, guaranteed savings or completed projects. "
"Create three distinctive 15-second kinetic typography motion reels with "
"dynamic graphics, music and voiceover. "+RUN_TAG)

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
