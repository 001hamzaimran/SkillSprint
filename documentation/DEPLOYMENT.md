# Railway backend and Vercel frontend

The repository contains hosting configuration, not a completed deployment. Replace the backend URL placeholders before publishing. Keep production data separate from tests and the fictional demo dataset.

## 1. Railway

1. Create a Railway project with PostgreSQL and a service connected to this repository. Use the repository root, not `frontend`, for the backend.
2. The root `railway.json` selects the Dockerfile and `/health` health check. The container initializes application tables and the first administrator, then starts Uvicorn on Railway's `PORT`.
3. Attach a persistent volume at `/data/uploads` and set `UPLOAD_DIR=/data/uploads`. Uploaded originals are private filesystem files, so an ephemeral container is insufficient. Back up the volume and PostgreSQL together.
4. Configure these backend variables in Railway, not in Git:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Railway PostgreSQL connection reference |
| `POSTGRES_SCHEMA` | `skillsprint` |
| `APP_ENV` | `production` |
| `APP_SECRET_KEY` | Unique random secret, at least 32 characters |
| `BOOTSTRAP_ADMIN_EMAIL` | Your administrator email |
| `BOOTSTRAP_ADMIN_PASSWORD` | Unique password, at least 12 characters |
| `OPENAI_API_KEY` | Your server-side API key |
| `GENAI_PROVIDER` | `openai` |
| `GENAI_MODEL` | Your supported structured-output model |
| `SESSION_COOKIE_SECURE` | `true` |
| `APP_BASE_URL` | Full HTTPS Railway backend URL |
| `FRONTEND_URL` | Full HTTPS production Vercel URL, without a trailing slash |
| `ALLOWED_ORIGINS` | Exact production Vercel origin; comma-separated if needed |
| `UPLOAD_DIR` | `/data/uploads` |
| `RUN_WORKER` | `true` |
| `MAX_UPLOAD_MB` | `10` |

5. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, and `SMTP_STARTTLS` for real password recovery. Production deliberately does not display reset links.
6. Start with one backend replica and one Uvicorn process. The background worker runs in that process; uploads are on the attached volume. Horizontal scaling requires shared file storage and a separately designed worker deployment.
7. Generate a public HTTPS domain and confirm `/health` succeeds. Initialization does not reset an existing administrator password. Do not seed fictional company records into a real company workspace.

## 2. Vercel

1. Import the same repository and select **`frontend` as Root Directory**. Framework: Vite. Build: `npm run build`. Output: `dist`.
2. In `frontend/vercel.json`, replace **every** `https://REPLACE-WITH-YOUR-BACKEND.up.railway.app` with the actual Railway HTTPS origin. Commit that configuration and deploy.
3. Keep the frontend API path `/api`. The rewrites proxy API and authenticated downloads through the Vercel origin. Do not switch to direct cross-site API calls without redesigning cookie/CSRF settings.
4. Put no database credentials, API keys, bootstrap passwords, or SMTP secrets in Vercel/Vite client variables. This frontend does not need them.
5. Set Railway's `FRONTEND_URL` and `ALLOWED_ORIGINS` to the resulting production Vercel URL and redeploy the backend. Use exact origins, not `*`. Preview deployments need explicit approval/origin configuration and should use a separate non-production backend.

## 3. Acceptance checks after deployment

1. Sign in through Vercel; refresh a nested route and confirm the session survives. Inspect failed requests if login loops: verify URL replacements, secure cookies, and exact origins.
2. Create a role, employee, employee login, and manager assignment. Confirm an employee cannot read another employee's plan or reviewer endpoints.
3. Upload a fictional PDF/DOCX; activate it, extract candidates, review requirements and rules, then generate a plan. Poll the job until completion; generation is asynchronous.
4. Review validation, publish, and complete checklist, quiz, and practical work as the employee. Grade as the assigned manager/reviewer and verify progress.
5. Exercise password-reset email, one-time reset, exports, source download, rejected invalid upload, and a failed-job retry.
6. Upload a newer policy version, inspect impact, activate, selectively regenerate, then review and publish the new draft.
7. Restart/redeploy Railway and confirm documents still download and progress survives. Verify backups through a restore to a separate environment.
8. Measure generation latency, concurrent-user capacity, and availability on the deployed services. Local functional tests do not establish the SRS 30-second, scale, or uptime targets.

## Local database issue observed

The installed PostgreSQL service was listening on port **5433**, while the local configuration targeted **5432**; the `skillsprint` database was not present on that service. Select the intended service, create the database, and update the local `DATABASE_URL` accordingly. No credentials or existing database configuration were changed automatically. Tests use isolated temporary schemas, not the production schema.

For local recovery links, set `FRONTEND_URL=http://localhost:5173` when using Vite, or `FRONTEND_URL=http://127.0.0.1:8000/app` when using the built React UI served by FastAPI. Production uses the Vercel origin without `/app`.

## Provider references

- [Vercel external rewrites](https://vercel.com/docs/routing/rewrites)
- [Vercel project configuration](https://vercel.com/docs/project-configuration/vercel-json)
- [Railway health checks and PORT](https://docs.railway.com/deployments/healthchecks)
- [Railway services and persistent storage](https://docs.railway.com/services)
