"""Load local .env without an external package, then launch app on localhost."""
import os, pathlib
for line in (pathlib.Path(__file__).parent/'.env').read_text(encoding='utf-8').splitlines() if (pathlib.Path(__file__).parent/'.env').exists() else []:
    line=line.strip()
    if not line or line.startswith('#') or '=' not in line:continue
    key,value=line.split('=',1)
    key=key.strip();value=value.strip().strip('"').strip("'")
    if key and value:os.environ.setdefault(key,value)
import uvicorn
if __name__=='__main__':uvicorn.run('app:app',host='127.0.0.1',port=8001)
