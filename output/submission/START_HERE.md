# SkillSprint AI — local submission pack

Deployment was removed from Phase 4 by the user. The application runs locally at http://127.0.0.1:8000 using MongoDB.

1. **PROJECT_REPORT.md** — architecture, database, data flow, use-case, activity and sequence diagrams; design and limits.
2. **ACCEPTANCE_MATRIX.csv** — all 63 numbered SRS steps, implementation evidence and known gaps.
3. **EVALUATION_REPORT.md** — 70 tests, ten full role plans, 880 comparisons, failure/security and performance findings.
4. **TECHNICAL_BLOG.md** — updated Medium-oriented article covering React/PostgreSQL, Railway/Vercel and recent navigation fixes; not published. **MEDIUM_PUBLISHING_NOTES.md** contains title/subtitle, suggested tags, screenshots and the pre-publication checklist. The older ZIP and manifest have not been rebuilt for this revision.
5. **SkillSprint_local_walkthrough.mp4** — silent annotated screen-based replay. VIDEO_NOTES.md and DEMO_SCRIPT.md explain coverage and full live-recording steps.
6. **TEAM_CONTRIBUTION.md** — honest solo/AI contribution and pending participant verification.
7. **../../reports/phase4/** — machine-readable test, capacity, provider and comparison evidence.

## Reproduce

Follow the root README for Python/MongoDB setup and local credentials. Use `python -m pytest -q`. Run `python scripts/benchmark_phase4.py` for the disposable capacity sample. `python scripts/evaluate_phase4_live.py` is billable and generates all ten complete 88-item role plans; it can take roughly 18 minutes with four evaluation workers. `python scripts/evaluate_hidden_ready.py` makes three additional small real API requests. Reports preserve original failure states.

The original fictional dataset, prompts, schema export and source code are included in SkillSprint_local_submission.zip. SHA256_MANIFEST.json records packaged file hashes. The archive excludes .env, private uploads, virtual environments and local caches.

## Owner actions that remain

Independently inspect and understand the AI-assisted code and content; replace this pending verification with your actual record. Review and publish the blog/repository if the competition requires public links. Record the full live-action demo using DEMO_SCRIPT.md if required, since the supplied MP4 is a replay. Select a redistribution license if desired; LICENSE currently reserves rights. Genuine five-day history cannot be fabricated. These limits and the unmet full-plan performance target are not hidden by the local packaging completion.
