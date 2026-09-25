# Phase 2 — Learning, review and assessment

Implemented locally on 2026-09-24. This phase corresponds to “Complete learning and review” in the four-phase roadmap. It does not claim full SRS completion.

## Features delivered

- Live structured generation creates a lesson, objective, checklist, workplace scenario, expected scenario response, multiple-choice quiz, answer explanation, practical task and point-based rubric for each requirement. Requirements are generated in batches of four; worker leases renew between calls. Provider errors remain visible failures.
- Reviewers can comment, reject, approve and publish. Publication requires explicit confirmation of content/answer/rubric review, current sources, successful independent core checks and complete assessment structures. It assigns one current plan to the employee.
- Editors and reviewers can revise each module using a form. Saving creates a new draft with a link to its original and fresh validation; it never overwrites the original content or learner history. Regeneration also creates a separate draft.
- Employees have a My Sprint workspace with lessons, checklists, source evidence, quiz attempts, scenario/practical submissions, stage milestones, mandatory completion and overdue indicators.
- The server grades the quiz against the published answer key. Answer keys and expected scenario responses are removed from employee plan views and JSON exports. Explanations appear after an attempt.
- Reviewers and assigned managers assess practical/scenario submissions using the published rubric. Scores are bounded by each criterion. The pass threshold is 80%; unsuccessful submissions can be revised and submitted again. Prior assessments remain stored.
- Module completion requires lesson acknowledgement, every checklist step, a passing quiz attempt and a passing human assessment. Prerequisites block premature submissions. Completion is distinct from source validation.
- Recommendations identify failed knowledge checks or practical assessments and link the learner back to the module and feedback. These are deterministic recommendations, not claims of AI diagnosis.
- Existing employee profiles can be linked to employee login accounts; one login maps to at most one employee profile.
- Review, learner and assessment actions have persisted audit events. Stale, draft and previously assigned versions cannot accept new learner submissions.

## How to use

1. As admin, create an employee account in **Access management**. In **People**, use **Link login** on the desired profile. New profiles can also be linked during creation.
2. Approve relevant source documents and requirements, then generate a plan. Existing Phase 1 plans must be regenerated to obtain Phase 2 assessments.
3. Inspect every module and its answer key. Correct content with **Edit this module as a new draft**, or add review comments/reject it.
4. Under **Review and publish**, select **Approve and publish**, write notes and confirm the content review. Publication assigns that version.
5. Sign in as the linked employee and open **My Sprint**. Save checklists, take quizzes and submit fictional practice work.
6. Sign in as a reviewer, admin or assigned manager. Open **Assessments**, score each rubric criterion and provide actionable feedback.
7. Reopen the learner’s progress to see scores, milestone completion and areas to revisit.

## Evidence and limitations

The automated suite covers Phase 1 regressions and Phase 2 permissions, publication gates, key redaction, score tampering, resubmission, persistent progress, source changes, immutable edits, unique account linking, prerequisites and multi-batch generation. The final suite contains 20 tests (9 Phase 1 and 11 Phase 2).

`reports/phase2_live_smoke.json` records a real OpenAI run from eight approved fictional SOP-11 requirements. It produced eight complete modules with 100% mandatory coverage (7/7) and 100% source traceability. Two batches required three total provider attempts; generation and validation took **115.13 seconds**. This exceeds the SRS 30-second target. Performance optimization and broader timing/capacity evidence remain Phase 4 work.

The same isolated smoke test exercised publication, eight quiz attempts, eight practical submissions and eight grading actions. Submitted work and grades were explicitly synthetic workflow-test data; they do not establish real learner competency or human verification of generated content. Test databases are removed after the test.

Browser QA exercised publication, checklist persistence, a failed quiz and successful retry, submission, assessor feedback and 100% completion, with desktop and mobile layout checks. It used a separate disposable database, not the main workspace.

Human review is still necessary for the meaning and correctness of generated prose, quiz answers and rubrics. The app checks assessment structure and evidence identity; it does not automatically prove semantic correctness. Phase 3 adds advanced conflict/condition/exception checks, consistency comparisons, selective policy updates and reports. Phase 4 adds full evaluation, performance work, deployment and submission artifacts. Replacing an assigned plan currently starts a separate progress record; selective carry-forward is Phase 3.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/live_phase2_smoke.py
```

The second command makes real billable API requests with fictional policy material. Normal tests use explicit test providers and do not contact OpenAI. `scripts/browser_phase2_fixture.py` starts a disposable synthetic UI test on port 8001 and removes its database when stopped normally.
