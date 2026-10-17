"""Import a completed real HeyGen motion reel into private Supabase Storage.

Requires explicit source URL from the generated HeyGen video, verifies MP4
bytes and supports no generated poster substitutions or publicly hosted UI.
"""
import os
from urllib.parse import urlparse
from urllib.request import Request,urlopen
import production_media as media

def import_reel(batch_id):
    url=os.getenv('MATRIX_COMPLETED_VIDEO_SOURCE','')
    if not url:return 'not_requested'
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='resource2.heygen.ai' or not parsed.path.endswith('.mp4'):
        raise RuntimeError('Video source not on verified HeyGen delivery domain')
    row=media.media_record(batch_id,1,'video')
    if row and row.get('status')=='completed':
        return 'already_archived'
    req=Request(url,headers={'User-Agent':'Matrix360-Production-Asset-Importer/1.0'})
    with urlopen(req,timeout=90) as resp:
        typ=resp.headers.get('Content-Type','').lower()
        if 'video' not in typ and 'octet-stream' not in typ:
            raise RuntimeError('Completed provider source not a video response')
        raw=resp.read(100*1024*1024+1)
    if not 10000<len(raw)<=100*1024*1024 or raw[4:8]!=b'ftyp':
        raise RuntimeError('Completed provider source has invalid MP4 signature or size')
    path=f'{batch_id}/video/1.mp4'
    media.upload_media(path,raw,'video/mp4')
    media.set_record(batch_id,1,'video','completed',object_path=path,provider_job_id='heygen_verified_0879283797ec4e05bc29529e5c5bffe3')
    return 'heygen_motion_mp4_archived'
