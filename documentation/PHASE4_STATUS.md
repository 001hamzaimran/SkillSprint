# Phase 4 — local evaluation and submission packaging

Historical evaluation snapshot, before the latest PostgreSQL/React SRS work. These results are not a fresh benchmark of the current build. Deployment is now in scope: Railway backend and Vercel frontend, as requested on 2026-09-27. See [deployment instructions](DEPLOYMENT.md). This is not a claim of complete SRS acceptance or externally published submission.

- 70 automated tests passed, including ten adversarial PDFs, ten reviewed conflict fixtures, ten actual policy-version transitions and provider failure boundaries.
- Ten full real role plans generated: 88 items each, 880 requirement comparisons. All passed core checks; all remain subject to human interpretation/review warnings.
- Three unfamiliar-role DOCX runs passed, taking 15.453, 15.027 and 11.599 seconds for four requirements each.
- Full 88-module runs took 333.112–483.878 seconds; the SRS 30-second full-plan target remains unmet.
- The 1,000-plan report median improved from 20.87 seconds to 3.12 seconds on a synthetic local capacity fixture. Request-scoped matrix reuse and narrower source queries caused the improvement.
- Local artifacts: project report/diagrams, 63-step acceptance matrix, evaluation/security findings, 2,590-word blog draft, annotated MP4 replay, demo script, schema export, source/data/evidence ZIP and hash manifest.

Read output/submission/START_HERE.md. Public repository/blog publication, full live-action video recording and participant human verification remain explicitly pending owner actions. Live deployment and acceptance checks are pending. No genuine prior Git history was fabricated.
