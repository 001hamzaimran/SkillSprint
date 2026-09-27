# SkillSprint AI

PostgreSQL-backed onboarding workspace built with Python, FastAPI, React and Jinja2. Source-to-plan generation, human review and publication, employee learning, assessments and persisted progress are connected through the React interface. Additional workflows include review queues, configurable stage deadlines, profile editing, search, progress insights, password recovery and controlled advisory overrides. Full competition SRS acceptance is still in progress.

Hosting target: **Railway backend + PostgreSQL, Vercel React frontend**. Follow [the deployment guide](documentation/DEPLOYMENT.md); the Vercel backend URL placeholders must be replaced before publishing. Historical evaluation evidence is recorded in [Phase 4 status](documentation/PHASE4_STATUS.md), not proof of acceptance for the current build.

See [the SRS implementation and acceptance map](documentation/SRS_COVERAGE.md) for the implemented workflows and remaining verification/performance gaps.

## Start this workspace

### React frontend

Build the frontend once, and rebuild it after frontend changes:

```powershell
cd D:\Personal\SkillSprint\frontend
npm ci
npm run build
cd ..
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000/app to use React. The `/api` endpoints, session cookies,
uploads and downloads are served by the same FastAPI application. The original
server-rendered interface remains at `/`.

For frontend development, keep the backend running and run `npm run dev` from
`frontend/` in a second terminal. Open http://localhost:5173. Vite proxies API and
download requests to the backend. Python `--reload` does not rebuild React.

PostgreSQL must be running and the database named by `DATABASE_URL` must exist. Application tables are created inside `POSTGRES_SCHEMA`.

If Docker is installed, start the included development database with `docker compose up -d postgres`. Otherwise install PostgreSQL 15+ and create the `skillsprint` database manually. Change the development password in `.env` for any non-local deployment.

```powershell
cd D:\Personal\SkillSprint
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe run.py
```

Open http://127.0.0.1:8000. Sign in as `admin@skillsprint.local` using `BOOTSTRAP_ADMIN_PASSWORD` from your local `.env`. Changing that variable after initialization does not change an existing account's password. `start.ps1` also starts the application. Stop the terminal server with Ctrl+C.

## Fresh installation

Use Python 3.11 or newer and PostgreSQL 15 or newer. Create the database first, for example:

```powershell
createdb -U postgres skillsprint
```

Then install the application:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Copy the example only on a fresh installation; preserve an existing `.env`. Set `APP_SECRET_KEY` to a random secret of at least 32 characters, `BOOTSTRAP_ADMIN_PASSWORD` to a unique password of at least 12 characters, and `OPENAI_API_KEY` to your own key. Configure `DATABASE_URL` and `POSTGRES_SCHEMA` as needed. No AssemblyAI or SMTP credentials are required.

Password recovery works without SMTP during local development by showing a one-time link on the confirmation page. For production, configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` and `SMTP_STARTTLS`; production never displays reset tokens in the browser.

```powershell
.\.venv\Scripts\python.exe manage.py init --seed-company
.\.venv\Scripts\python.exe run.py
```

Initialization imports 20 fictional AsterBridge PDFs, 10 job roles and one demo employee. Documents and extracted requirements begin as drafts. Re-running initialization does not duplicate these records or reset credentials.

## Migrating an existing MongoDB workspace

Keep the old MongoDB service running temporarily, start PostgreSQL, and select an empty destination schema in `.env`. Install the legacy source driver only for the migration, then copy the records:

```powershell
.\.venv\Scripts\python.exe -m pip install "pymongo>=4.11,<5"
$env:MONGO_SOURCE_URI="mongodb://localhost:27017"
$env:MONGO_SOURCE_DATABASE="skillsprint"
.\.venv\Scripts\python.exe scripts\migrate_mongodb_to_postgres.py
.\.venv\Scripts\python.exe manage.py check
```

The migration refuses to write into a non-empty PostgreSQL schema. Original uploaded files stay in `uploads/` and must remain beside the migrated database.

## Demo workflow

1. Open **Knowledge library** and inspect a document, its extracted sections and requirement candidates. You can also upload a PDF or DOCX with its version, effective date and role scope.
2. Activate the source, then review each candidate against its source passage. Approve the correct role, mandatory status and deadline. Admins and reviewers can approve; AI output never automatically becomes approved evidence.
3. Open **Role matrix** to inspect approved requirements. Under **People**, create or select an employee with a matching job role and generate a plan.
4. Wait for the persisted job to finish. Inspect the plan's coverage, source traceability, validation findings and source links; download its JSON.
5. Create an employee login in **Access management** and link it under **People → Link login**. Review lessons, quiz answers and rubrics, then **Approve and publish** the plan.
6. Sign in as the linked employee and use **My Sprint** to complete checklists, quizzes and practical submissions. A reviewer or assigned manager grades submissions under **Assessments**.
7. Activate a newer source version to mark affected plans stale. Preview policy impact before activation, then use the assigned plan’s selective update action. Review and publish the new version to carry forward eligible unchanged work.

Only active documents and approved requirements enter generation. Suspicious instruction-like source content is quarantined. A plan that passes core checks still requires human review of generated teaching content.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests require local PostgreSQL and use isolated temporary schemas. They do not call the live AI API. The optional integration smoke test makes a real, billable OpenAI request with fictional company content:

```powershell
.\.venv\Scripts\python.exe scripts/live_phase2_smoke.py
```

It uses and removes an isolated test database and writes `reports/phase2_live_smoke.json`. The recorded run generated eight full modules in 115.13 seconds over two batches (three provider attempts), with 100% mandatory coverage and traceability. It also tested publication, quiz attempts, submissions and grading using synthetic test work. The SRS 30-second performance target remains unmet; this is not a capacity benchmark.

## Implementation and limits

Application modules live in `app/`; prompts in `prompt_templates/`; UI in `frontend/`, `templates/` and `static/`. PostgreSQL stores users, expiring sessions, roles, employees, source metadata, reviewed requirements, leased jobs, plans and audit events in JSONB-backed application tables. Original files remain in private `uploads/` storage. Back up PostgreSQL and uploads together.

Python code uses Black with a 100-character line length. Run
`.\.venv\Scripts\python.exe -m black app scripts tests manage.py run.py` before
submitting code changes. Recoverable caches and temporary build artifacts are
kept in `archive_unused/`; see its README for the inventory.

The local server binds to loopback and runs one embedded worker. Keep `RUN_WORKER=true` for this setup. Phase 3 adds reviewed structured rules, conflict precedence, prerequisite checks, controlled consistency runs, comparison views, selective updates and filtered CSV reports. Unchanged progress is carried forward only for eligible selective updates; old work remains in history. Phase 4 local evaluation and packaging are delivered; deployment was removed by user request. See output/submission/START_HERE.md for evidence and remaining owner actions. Practical work requires a human assessor. Existing Phase 1 plans need regeneration before publication. Scanned PDFs require OCR before upload. Source filtering is a defense, not a guarantee against all prompt injection. Free-text factual accuracy needs human review.

Keep `.env` private and out of source control. The generated company pack is fictional competition material, not real company policy. See `PROJECT_PLAN.md`, `AI_USAGE.md` and `documentation/POSTGRESQL_DESIGN.md` for current persistence details.

## Phase 4 evidence

Run `python -m pytest -q` for the 70-test suite. Reports under `reports/phase4/` include ten complete real role plans, 880 comparisons and local capacity measurements. Open `output/submission/START_HERE.md` for the local submission pack. Optional video-building dependencies are in `requirements-artifacts.txt`; they are not required to run the application. Deployment is outside this delivery scope.
