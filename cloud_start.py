"""Fail-closed Render startup. Preserve existing app's BASE/data paths via a symlink."""
import os, pathlib, shutil, secrets, sys
ROOT=pathlib.Path(__file__).resolve().parent
DATA=ROOT/'data'

def prepare():
    if os.environ.get('MATRIX360_CLOUD_MODE') != '1':
        return
    secret=os.getenv('MATRIX360_API_KEY','').strip()
    if len(secret)<32 or secret=='REPLACE_WITH_A_LONG_RANDOM_SECRET':
        sys.exit('ERROR: MATRIX360_API_KEY must be a random secret of at least 32 characters')
    director=os.getenv('MATRIX360_DIRECTOR_KEY','').strip()
    if len(director)<32 or director==secret:
        sys.exit('ERROR: distinct MATRIX360_DIRECTOR_KEY (32+ characters) required')
    if os.getenv('MATRIX360_FREE_PREVIEW') == '1':
        # Free Render instances have no persistent filesystem. This is explicitly
        # disposable test data, NOT a durable approvals workflow.
        DATA.mkdir(parents=True, exist_ok=True)
        if not (DATA/'brand_profile.json').is_file():
            sys.exit('ERROR: bundled brand profile missing')
        (DATA/'renders').mkdir(exist_ok=True)
        return
    target=pathlib.Path(os.getenv('MATRIX360_DATA_ROOT','/var/data')).resolve()
    if not target.is_dir():sys.exit(f'ERROR: Persistent disk missing: {target}')
    profile=target/'brand_profile.json'
    if not profile.exists():shutil.copy2(DATA/'brand_profile.json', profile)
    (target/'renders').mkdir(exist_ok=True)
    if DATA.is_symlink():
        if DATA.resolve()!=target:sys.exit('ERROR: data symlink target mismatch')
    else:
        # The image must contain only seed brand_profile.json + optional empty renders.
        other=[p for p in DATA.iterdir() if p.name not in ('brand_profile.json','renders')]
        if other:sys.exit('ERROR: Unexpected files in image data directory; aborting to avoid accidental data loss')
        shutil.rmtree(DATA)
        DATA.symlink_to(target, target_is_directory=True)

def storage_preflight():
    """Safe startup status only: never emit secrets, object bytes or URLs."""
    import reference_persistence as store
    key=os.getenv('MATRIX_REFERENCE_SUPABASE_SERVICE_KEY','')
    key_type=('modern_secret' if key.startswith('sb_secret_') else
              'publishable_wrong_role' if key.startswith('sb_publishable_') else
              'legacy_jwt' if key.count('.')==2 else
              'other_or_missing')
    try:
        if store.settings() is None:
            result='not_configured'
        else:
            try:
                import reference_grid as grid
                if grid.restore_gate_record():
                    # Verify both the reconstructed registry and local bytes.
                    with grid.dbconn() as db:
                        record=db.execute("SELECT id FROM reference_grid WHERE role='locked_gate_master' AND status='verified' AND sha256=?",(grid.GATE_SHA,)).fetchone()
                    local=grid.STORE/(record[0]+'.png') if record else None
                    import hashlib
                    result=('master_restored_and_verified' if local is not None and local.is_file()
                            and hashlib.sha256(local.read_bytes()).hexdigest()==grid.GATE_SHA
                            else 'recovery_not_verified')
                else:
                    result='remote_master_unavailable'
            except store.StorageError as exc:
                # Only controlled, internally authored exception messages.
                result=str(exc)
    except store.StorageError as exc:
        result=str(exc)
    print('MATRIX360_REFERENCE_PREFLIGHT key_type='+key_type+' result='+result,flush=True)

def ai_storage_preflight():
    """Non-secret REST readiness check. No model calls or sensitive data in logs."""
    import durable_campaign_store as campaign_store
    try:
        if not campaign_store.is_configured():
            state='not_configured'
        else:
            campaign_store.list_batches()
            state='remote_read_verified'
    except campaign_store.CampaignStoreError as exc:
        state=str(exc)
    print('MATRIX360_AI_DURABILITY_PREFLIGHT result='+state,flush=True)

if __name__=='__main__':
    prepare()
    storage_preflight()
    ai_storage_preflight()
    import uvicorn
    port=int(os.environ.get('PORT','10000'))
    uvicorn.run('app:app',host='0.0.0.0',port=port,proxy_headers=True)
