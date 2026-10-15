# Matrix360 SocialManager — Render Free PREVIEW

This folder is the consolidated Lakhotia pilot (v1.3), configured for **temporary testing** on Render's Free Docker service. It is not a durable campaign-management or production system. No social publishing or ad spend is enabled.

## GitHub Desktop

Clone `Matrix360repo/SocialManager`, copy **all contents of this folder** into the repository root, and check the change list before committing to `main`. Do not commit `.env`, `*.sqlite3`, `data/renders/*.png`, or secrets. Use a feature branch if possible, e.g. `render-free-preview`, and merge only after review. Set repository visibility to private.

## Render — create a Web Service (not Blueprint)

- Repository: `Matrix360repo/SocialManager`; branch containing these files
- Language: `Docker`; Root Directory: **blank**; region: your choice; compute: **Free**
- The Dockerfile runs `python cloud_start.py`; no custom command required.
- Configure the following Environment variables, entered **separately**:
  - `MATRIX360_CLOUD_MODE=1`
  - `MATRIX360_FREE_PREVIEW=1`
  - `MATRIX360_API_KEY=<random 32+ character secret>` (Render Generate button; save securely)
  - `OPENAI_API_KEY=<your private OpenAI key>` (optional if using Groq)
  - `MATRIX_MODEL=gpt-4.1-mini`
  - `GROQ_API_KEY=<your private Groq key>` (optional if using OpenAI)
  - `GROQ_MODEL=llama-3.3-70b-versatile`
  - `MATRIX_AI_PROVIDER=groq` (optional: force 'groq' or 'openai' when both keys are present)
- Do **not** configure `MATRIX360_DATA_ROOT` or a persistent disk in Free preview mode.
- Test `https://YOUR-SERVICE.onrender.com/health` (public health endpoint).
- Main dashboard requires HTTP Basic authentication; **any username**, password is `MATRIX360_API_KEY`. For n8n requests, set header `X-Matrix360-Key` to that same secret.

## Critical limitations

- Free instances can sleep, restart or redeploy; any SQLite drafts, revisions, approval events and PNGs saved on the instance can **disappear without warning**. Do not use for real client approvals or production records.
- OpenAI/Groq API charges or rate limits are separate from Render hosting.
- The bundled brand profile and official logo are needed for successful startup/rendering.
- Model calls are not verified against your actual OpenAI/Groq account at boot; test them after deployment.
- Do not publish, schedule, or advertise automatically. Human approval is required.
- For durable deployment, upgrade to persistent disk or migrate assets/records to managed database/object storage and remove Free Preview mode.
