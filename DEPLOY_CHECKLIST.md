# Deployment verification — FREE PREVIEW

1. Confirm repository root has `Dockerfile`, `cloud_start.py`, `app.py`, `engine.py`, `requirements.txt`, `assets/lakhotia_group_logo_official.png`, `assets/consultation_reference.png`, `data/brand_profile.json`.
2. Confirm `.env` and any `*.sqlite3` / `data/renders/*.png` are absent from Git tracked files.
3. Set cloud, preview and authentication variables in Render. Do not post secrets.
4. Deploy Free Docker service; check `/health` reports `status: ok`.
5. Open `/` using HTTP Basic (username arbitrary, password equals MATRIX360_API_KEY).
6. Generate one draft; review 3 PNG previews; request revision; approve a version; export ZIP.
7. Confirm actual AI provider (OpenAI or Groq, not `offline_template`) if testing AI.
8. EXPECT HISTORY LOSS after a free instance restarts or redeploys.
