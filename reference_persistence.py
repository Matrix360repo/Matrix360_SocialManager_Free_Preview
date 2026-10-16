"""Private, immutable Supabase Storage recovery for the sole approved Lakhotia gate.

No public bucket or anonymous access. Remote object path is deterministic by SHA.
The trusted checksum is pinned locally and verified on every restore. No AI fallback.
"""
import hashlib
import os
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

GATE_SHA='9ccf79e7f6d7ed22c6f65ed8632d2eb29f6bb6e7056f14f9a3f8d82f905430f5'
GATE_PATH=f'lakhotia/architectural-masters/{GATE_SHA}.png'
MAX_BYTES=24*1024*1024

class StorageError(RuntimeError):
    pass

def settings():
    url=os.getenv('MATRIX_REFERENCE_SUPABASE_URL','').strip().rstrip('/')
    bucket=os.getenv('MATRIX_REFERENCE_SUPABASE_BUCKET','').strip()
    key=os.getenv('MATRIX_REFERENCE_SUPABASE_SERVICE_KEY','').strip()
    if not any((url,bucket,key)):
        return None
    parsed=urlparse(url)
    if (not all((url,bucket,key)) or parsed.scheme!='https' or not parsed.netloc
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or '/' in bucket or bucket in ('.','..')):
        raise StorageError('Invalid or incomplete private reference-storage configuration')
    return (url,bucket,key)

def _request(method, raw=None):
    cfg=settings()
    if cfg is None:
        raise StorageError('Private reference storage is not configured')
    url,bucket,key=cfg
    object_url=url+'/storage/v1/object/'+quote(bucket,safe='')+'/'+quote(GATE_PATH,safe='/')
    headers={'apikey':key,'Authorization':'Bearer '+key}
    if method=='POST':
        headers.update({'Content-Type':'image/png','x-upsert':'false'})
    request=Request(object_url,data=raw,headers=headers,method=method)
    try:
        with urlopen(request,timeout=25) as response:
            if method=='GET':
                result=response.read(MAX_BYTES+1)
                if len(result)>MAX_BYTES:
                    raise StorageError('Remote asset exceeded 24 MB limit')
                return result
            return response.status
    except HTTPError as exc:
        # Never expose key, headers or provider response contents.
        raise StorageError('Private reference storage returned HTTP '+str(exc.code)) from None
    except (URLError,TimeoutError,OSError) as exc:
        raise StorageError('Private reference storage is unreachable') from None

def check(raw):
    if hashlib.sha256(raw).hexdigest()!=GATE_SHA:
        raise StorageError('Refusing architectural master with non-matching SHA-256')
    return raw

def backup_gate(raw):
    check(raw)
    if settings() is None:
        return False
    try:
        _request('POST',raw)
    except StorageError as exc:
        # Supabase immutability: a preexisting object is acceptable ONLY when
        # it can be read and independently checksum verified.
        if 'HTTP 409' not in str(exc):
            raise
        existing=fetch_gate()
        check(existing)
    return True

def fetch_gate():
    raw=_request('GET')
    return check(raw)

def recover_to(path:Path):
    # An invalid local copy must NEVER be silently treated as a valid reference.
    if path.exists():
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()==GATE_SHA:
            return raw
    raw=fetch_gate()
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.restoring')
    try:
        temp.write_bytes(raw)
        if hashlib.sha256(temp.read_bytes()).hexdigest()!=GATE_SHA:
            raise StorageError('Restored reference checksum mismatch')
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)
    return raw
