"""Server-side durable Supabase PostgREST storage for Director AI approvals.

No browser keys, no anonymous RLS policy. Calls only with configured server secret.
"""
import json
from urllib.parse import quote
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import reference_persistence as gate_store

class CampaignStoreError(RuntimeError):pass

TABLES={'batches':'matrix360_lakhotia_ai_batches',
        'reviews':'matrix360_lakhotia_ai_reviews',
        'audit':'matrix360_lakhotia_ai_audit',
        'media':'matrix360_lakhotia_ai_media',
        'reel_reviews':'matrix360_lakhotia_reel_reviews',
        'reel_audit':'matrix360_lakhotia_reel_audit'}

def is_configured():
    return gate_store.settings() is not None

def api(table,method='GET',filters='',payload=None,prefer=''):
    if table not in TABLES:raise CampaignStoreError('Unknown table')
    cfg=gate_store.settings()
    if not cfg:raise CampaignStoreError('Durable AI store is not configured')
    url,bucket,key=cfg
    endpoint=url+'/rest/v1/'+TABLES[table]+('?'+filters if filters else '')
    headers={'apikey':key,'Authorization':'Bearer '+key,
             'Accept':'application/json','Content-Type':'application/json'}
    if prefer:headers['Prefer']=prefer
    data=json.dumps(payload).encode('utf-8') if payload is not None else None
    req=Request(endpoint,data=data,headers=headers,method=method)
    try:
        with urlopen(req,timeout=20) as response:
            result=response.read(250000)
            return json.loads(result) if result else []
    except HTTPError as exc:
        # Do not leak credentials, payload, protected details or provider response.
        raise CampaignStoreError('Private AI campaign storage returned HTTP '+str(exc.code)) from None
    except (URLError,TimeoutError,OSError):
        raise CampaignStoreError('Private AI campaign storage is unreachable') from None

def save_batch(ident,created,brief,provider,model,payload):
    row={'id':ident,'client_id':'lakhotia','created_utc':created,'brief':brief,
         'provider':provider,'model':model,'payload':payload}
    api('batches','POST',payload=[row],prefer='return=minimal')

def list_batches():
    return api('batches','GET','select=id,created_utc,brief,provider,model&client_id=eq.lakhotia&order=created_utc.desc&limit=8')

def get_batch(ident):
    rows=api('batches','GET','select=*&client_id=eq.lakhotia&id=eq.'+quote(ident,safe=''))
    return rows[0] if rows else None

def get_reviews(ident):
    return api('reviews','GET','select=option_no,decision,note&batch_id=eq.'+quote(ident,safe=''))

def save_decision(ident,option,decision,note,now):
    review={'batch_id':ident,'option_no':option,'decision':decision,'note':note,
            'reviewer':'Director','reviewed_utc':now}
    # Audit log must precede mutable review. If an audit write fails, fail closed.
    api('audit','POST',payload=[{'batch_id':ident,'option_no':option,'decision':decision,
                                'note':note,'reviewer':'Director','created_utc':now}],
        prefer='return=minimal')
    api('reviews','POST','on_conflict=batch_id,option_no',payload=[review],
        prefer='resolution=merge-duplicates,return=minimal')

def reel_reviews(ident):
    return api('reel_reviews','GET','select=option_no,decision,note&batch_id=eq.'+quote(ident,safe=''))

def save_reel_decision(ident,option,decision,note,now):
    api('reel_audit','POST',payload=[{'batch_id':ident,'option_no':option,
       'decision':decision,'note':note,'reviewer':'Director','created_utc':now}],
       prefer='return=minimal')
    api('reel_reviews','POST','on_conflict=batch_id,option_no',
       payload=[{'batch_id':ident,'option_no':option,'decision':decision,
       'note':note,'reviewer':'Director','reviewed_utc':now}],
       prefer='resolution=merge-duplicates,return=minimal')
