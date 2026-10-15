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

if __name__=='__main__':
    prepare()
    import uvicorn
    port=int(os.environ.get('PORT','10000'))
    uvicorn.run('app:app',host='0.0.0.0',port=port,proxy_headers=True)
