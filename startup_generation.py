"""Execute the Director-authorized Oct 17 live production generation once.

Invoked at app startup after explicit Render opt-in. Records source outcome
without exposing secrets, and uses the same production media APIs as UI users.
"""
import os,threading
from security_roles import activate_actor,clear_actor

RUN_TAG='matrix360_oct17_director_authorized_live_generation_v1'
BRIEF=("Create a commercially publishable, premium industrial B2B campaign for "
       "Lakhotia Industrial Complex, Ranihati-Amta Road, Howrah. "
       "Create three clearly differentiated editorial photographic approaches "
       "for manufacturers, warehousing firms and logistics operators deciding "
       "where to expand in West Bengal. Emphasize practical industrial site "
       "selection, approx. 4 km proximity to NH-16 and the offer of free expert "
       "consultation, without claiming finished infrastructure. Use realistic "
       "illustrative industry photography of different human and industrial "
       "activities, without inventing or redrawing the Lakhotia gate or site. "
       "For reels use actual cinematic subject movement, operations and camera "
       "motion, not slideshow effects. "+RUN_TAG)

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
            print('MATRIX360_LIVE_GENERATION result=already_registered batch='+str(matched[0]['id']),flush=True)
            return
        print('MATRIX360_LIVE_GENERATION result=starting_real_provider_requests',flush=True)
        batch=create_ai_batch(BRIEF,'Manufacturing businesses','Consultation enquiries','Instagram','openai')
        print('MATRIX360_LIVE_GENERATION result=three_posts_three_reels_created batch='+str(batch['id']),flush=True)
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
