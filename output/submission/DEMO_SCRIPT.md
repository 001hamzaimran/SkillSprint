# Local evaluator and recording walkthrough

Deployment is excluded. Use README.md to initialize MongoDB and start the app at http://127.0.0.1:8000. The main workspace contains draft sources; no evaluation fixture was imported as a real approval or learner score.

For a safe replay, run `python scripts/demo_phase4.py` and open http://localhost:8001. The terminal prints an explicitly disposable demo login. Stop that process after use. This temporary workspace replays real Phase 3 output and synthetic state; it does not call the provider or alter the main database.

## Suggested seven-minute live recording

1. **00:00–00:40 — Login and roles.** Explain five application permission groups. Create an unfamiliar job role and fictional employee; distinguish job role from account privileges.
2. **00:40–01:30 — Upload.** Upload `hidden_test_ready/observatory_rehearsal.docx`. Show paragraph and table-cell extraction. Activate the fictional source and review candidates against exact passages. Explain that these approvals are a demonstration, not organizational authorization.
3. **01:30–02:10 — Matrix and generation.** Select the new role, inspect the complete matrix and queue generation. Show persisted job status. If waiting is edited out, label elapsed real time rather than implying instant generation.
4. **02:10–03:00 — Learning and JSON.** Inspect stages, objective, lesson, checklist, practical activity, scenario, quiz and rubric. Download JSON. Show exact requirement/source IDs and Python expected-versus-actual comparisons.
5. **03:00–03:45 — Real failures.** In the replay workspace inspect `/plans/demo-defect`, explicitly labeled a deliberately corrupted citation. Show reduced coverage and blocked publication. Select the conflict demonstration role in Verification and explain reviewed precedence.
6. **03:45–04:15 — Injection.** Upload an authored ADV PDF. Show quarantine and the blocked activation/AI-extraction actions. Do not claim that regex establishes general injection immunity.
7. **04:15–05:15 — Review and learning.** Review the plan against sources, publish a demonstration version, open a linked employee account, read/check/answer/submit fictional practical work, and grade it with reviewer feedback. Label all demonstration completions synthetic.
8. **05:15–06:20 — Update.** Upload a changed policy version, preview impact before activation, approve its requirements, and open selective update on the assigned plan. Show retained and regenerated modules. After real generation and review, publish and show unchanged progress copied. The earlier version remains in history.
9. **06:20–07:00 — Evidence.** Open Reports, filter/export CSV, show `reports/phase4/requirement_comparison.csv`, test results and performance limits. Explain that the 30-second full-plan target is unmet and hosting is out of this delivery scope.

## Supplied MP4 coverage

`SkillSprint_local_walkthrough.mp4` is a 170-second annotated screen-based replay with login, upload form, extraction, role form, matrix, generation result, quiz/rubric, Python citation failure, conflict view, injection quarantine, comparison, selective update preview, progress and reports. It is silent and not a continuous live interaction recording. It does not show a fresh upload/generation/publication taking place or a completed learner grading session. Use the script above for the competition's full live-action demonstration requirement; do not describe the supplied replay as covering those missing interactions.
