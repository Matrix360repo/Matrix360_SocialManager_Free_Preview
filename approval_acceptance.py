"""One-shot live REST/role regression; deletes its synthetic QA records.

This test never approves a real creative. It verifies that the same Director
endpoints used by the UI persist rejects/revisions and recover from Supabase.
"""
import os
import uuid
from datetime import datetime,timezone
from fastapi import HTTPException

from security_roles import activate_actor,clear_actor
import durable_campaign_store as store

FLAG="matrix360_issue29_director_rejections_retrieval_qa_v1"

def acceptance_test():
    from director_ai_studio import decide, decide_reel, batch_detail
    if not store.is_configured():raise RuntimeError("Private Supabase unavailable")
    ident=str(uuid.uuid4())
    time=datetime.now(timezone.utc).isoformat()
    payload={
        "candidates":[{"option":i,"headline":"INTERNAL QA - NEVER PUBLISH",
                         "caption":"Quality check only","pillar":"Internal QA"} for i in (1,2,3)],
        "checks":[{"option":i,"passed":True,"issues":[],
                    "human_approval_required":True} for i in (1,2,3)],
        "reels":[{"option":i,"headline":"INTERNAL QA - NEVER PUBLISH",
                  "video_prompt":"Internal test record with no media"} for i in (1,2,3)]
    }
    try:
        store.save_batch(ident,time,"INTERNAL DATA VALIDATION ONLY; NOT A CAMPAIGN",
                         "openai_api","internal-no-model-called",payload)
        op=activate_actor("operator")
        try:
            try:
                decide(ident,1,'rejected',"")
                raise RuntimeError("Operator was wrongly authorized")
            except HTTPException as exc:
                if exc.status_code!=403:raise
            try:
                decide_reel(ident,2,'revision_requested',"QA only")
                raise RuntimeError("Operator reel approval bypass")
            except HTTPException as exc:
                if exc.status_code!=403:raise
        finally:clear_actor(op)
        director=activate_actor("Director")
        try:
            decide(ident,1,'rejected',
                   "Automated QA only; no actual Director release approval")
            decide_reel(ident,2,'revision_requested',
                        "Automated QA: verify durable revision note")
        finally:clear_actor(director)
        # A fresh PostgREST read, same path as Director UI refresh.
        record=batch_detail(ident)
        if (record["reviews"].get("1",{}).get("decision")!="rejected" or
                record["reel_reviews"].get("2",{}).get("decision")!="revision_requested"):
            raise RuntimeError("Private Supabase approval decision was not persisted")
        audit=store.api("audit","GET","select=event_id&batch_id=eq."+ident)
        reel_audit=store.api("reel_audit","GET","select=id&batch_id=eq."+ident)
        if len(audit)!=1 or len(reel_audit)!=1:
            raise RuntimeError("Approval audit logs missing")
        return "director_review_roundtrip_passed"
    finally:
        # Cascade removes audit and review entries; QA never visible afterward.
        store.api("batches","DELETE","id=eq."+ident+"&client_id=eq.lakhotia",
                  prefer="return=minimal")

def startup():
    if os.environ.get("MATRIX_REVIEW_QA_ONCE")!=FLAG:return
    try:
        result=acceptance_test()
        print("MATRIX360_DIRECTOR_REVIEW_QA result="+result,flush=True)
    except Exception as exc:
        print("MATRIX360_DIRECTOR_REVIEW_QA result=failed type="+type(exc).__name__,flush=True)
