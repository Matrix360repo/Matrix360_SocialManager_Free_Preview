# Lakhotia reference auto-recovery: deployment runbook

## Current state
The code is compatible with disposable Render preview plus a **private** Supabase Storage bucket. The new storage integration does not change any existing secrets or create cloud resources. It persists **only** the SHA-locked official Lakhotia gate master, not the rest of the image gallery, draft approvals, or campaign database.

## One-time configuration (Director or infrastructure administrator)
1. Provision a private Supabase Storage bucket, e.g. `matrix360-architectural-masters`. Confirm that it is **not public** and anonymous clients cannot write to it.
2. Set the following **Render server-side environment variables** (never in GitHub source, HTML, screenshots, or ChatGPT):
   - `MATRIX_REFERENCE_SUPABASE_URL`: the exact HTTPS Supabase project base URL, such as `https://<project-ref>.supabase.co`.
   - `MATRIX_REFERENCE_SUPABASE_BUCKET`: the private bucket ID.
   - `MATRIX_REFERENCE_SUPABASE_SERVICE_KEY`: a backend-only credential with sufficient private object read/write permissions. Restrict its deployment scope; do not expose to browsers.
3. Redeploy once. If the verified original is still in the current Render ephemeral cache, visiting `/architectural-compositor` or `/reference-grid` automatically archives it. Otherwise the checksum-verified original must be restored **once**, as the private remote object did not exist before this change.
4. Visit authenticated `/api/reference-grid/storage-status`. Do not consider persistence live unless `remote_master_checksum_verified=true` and `survives_ephemeral_restart=true`.
5. Force a controlled redeployment; revisit the status endpoint and the compositor. The exact approved image must reappear without manual upload, with its official SHA-256 still verified.

## Security
- Remote object path: `lakhotia/architectural-masters/9ccf79e7f6d7ed22c6f65ed8632d2eb29f6bb6e7056f14f9a3f8d82f905430f5.png`.
- Source bytes are NEVER overwritten and always validated against the locked SHA-256.
- If the remote storage is unavailable, corrupted, or missing, the application refuses to synthesize a new master or substitute AI imagery.
- The storage key must have server-only scope; using a shared privileged key requires key-management review before commercial deployment.
- This is a single-master prototype. Production requires per-tenant storage permissions, audit log, object lifecycle policy, encryption and durable Postgres metadata.

## Human involvement
An authorized infrastructure administrator must set up the private bucket and secret once. Routine redeploys and matching gate retrieval should then be automatic. Director final creative/publication approval remains mandatory.
