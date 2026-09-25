# SkillSprint AI

MongoDB-backed onboarding workspace built with Python, FastAPI and Jinja2. Phases 1–3 provide source-to-plan generation, human review and publication, employee learning, quizzes, practical assessment and persisted progress. Full competition SRS coverage is still in progress; see [Phase 4 local evaluation and submission pack](documentation/PHASE4_STATUS.md).

## Start this workspace

MongoDB must be running locally on port 27017. The virtual environment, `.env`, administrator and draft sample documents are already configured on this computer.

```powershell
cd D:\Personal\SkillSprint
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe run.py
```

Open http://127.0.0.1:8000. Sign in as `admin@skillsprint.local` using `BOOTSTRAP_ADMIN_PASSWORD` from your local `.env`. Changing that variable after initialization does not change an existing account's password. `start.ps1` also starts the application. Stop the terminal server with Ctrl+C.

## Fresh installation

Use Python 3.11 or newer and MongoDB. In PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
Copy-Item .env.example .env
```

Copy the example only on a fresh installation; preserve an existing `.env`. Set `APP_SECRET_KEY` to a random secret of at least 32 characters, `BOOTSTRAP_ADMIN_PASSWORD` to a unique password of at least 12 characters, and `OPENAI_API_KEY` to your own key. Configure `MONGODB_URI` and `MONGODB_DB_NAME` as needed. No AssemblyAI or SMTP credentials are required.

```powershell
.\.venv\Scripts\python.exe manage.py init --seed-company
.\.venv\Scripts\python.exe run.py
```

Initialization imports 20 fictional AsterBridge PDFs, 10 job roles and one demo employee. Documents and extracted requirements begin as drafts. Re-running initialization does not duplicate these records or reset credentials.

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

Tests require local MongoDB and use isolated temporary databases. They do not call the live AI API. The optional integration smoke test makes a real, billable OpenAI request with fictional company content:

```powershell
.\.venv\Scripts\python.exe scripts/live_phase2_smoke.py
```

It uses and removes an isolated test database and writes `reports/phase2_live_smoke.json`. The recorded run generated eight full modules in 115.13 seconds over two batches (three provider attempts), with 100% mandatory coverage and traceability. It also tested publication, quiz attempts, submissions and grading using synthetic test work. The SRS 30-second performance target remains unmet; this is not a capacity benchmark.

## Implementation and limits

Application modules live in `app/`; prompts in `prompt_templates/`; UI in `templates/` and `static/`. MongoDB stores users, expiring sessions, roles, employees, source metadata, reviewed requirements, leased jobs, plans and audit events. Original files remain in private `uploads/` storage. Back up MongoDB and uploads together.

Python code uses Black with a 100-character line length. Run
`.\.venv\Scripts\python.exe -m black app scripts tests manage.py run.py` before
submitting code changes. Recoverable caches and temporary build artifacts are
kept in `archive_unused/`; see its README for the inventory.

The local server binds to loopback and runs one embedded worker. Keep `RUN_WORKER=true` for this setup. Phase 3 adds reviewed structured rules, conflict precedence, prerequisite checks, controlled consistency runs, comparison views, selective updates and filtered CSV reports. Unchanged progress is carried forward only for eligible selective updates; old work remains in history. Phase 4 local evaluation and packaging are delivered; deployment was removed by user request. See output/submission/START_HERE.md for evidence and remaining owner actions. Practical work requires a human assessor. Existing Phase 1 plans need regeneration before publication. Scanned PDFs require OCR before upload. Source filtering is a defense, not a guarantee against all prompt injection. Free-text factual accuracy needs human review.

Keep `.env` private and out of source control. The generated company pack is fictional competition material, not real company policy. See `PROJECT_PLAN.md`, `AI_USAGE.md` and `documentation/MONGODB_DESIGN.md` for project context.

## Phase 4 evidence

Run `python -m pytest -q` for the 70-test suite. Reports under `reports/phase4/` include ten complete real role plans, 880 comparisons and local capacity measurements. Open `output/submission/START_HERE.md` for the local submission pack. Optional video-building dependencies are in `requirements-artifacts.txt`; they are not required to run the application. Deployment is outside this delivery scope.
