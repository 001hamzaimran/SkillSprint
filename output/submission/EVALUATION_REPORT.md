# Phase 4 evaluation results

Executed locally on 2026-09-25. Deployment excluded by user request. This is an evidence report, not a claim of full SRS compliance.

| Evaluation | Result | Scope |
|---|---|---|
| Automated tests | 70 passed; 0 failures | JUnit: reports/phase4/tests.xml; one upstream Starlette/httpx deprecation warning |
| Full real role plans | 10/10 core checks passed | 88 generated items each; 880 actual expected/actual comparisons |
| Full generation latency | 333.11–483.88 seconds | Four evaluation workers; normal app uses one. 30-second full-plan target unmet |
| Small unfamiliar-role rehearsal | 3/3 passed | Four requirements per run; 15.453, 15.027, 11.599 seconds |
| Full report page median | 20.87s → 3.12s | Three requests before/after on 1,000 synthetic one-module plans |
| Adversarial PDFs | 10/10 quarantined and blocked | No generated plans, jobs, permission or completion changes |
| Conflict fixtures | 10/10 detected | Explicit reviewed fixture key/value annotations, not automatic semantic extraction |
| Policy version fixtures | 10/10 invalidate linked plans | Actual historical/current PDFs through upload and activation |
| Health sample | 30/30 succeeded | Short local sample; does not establish general 99% availability |

## Source and validation evidence

`reports/phase4/role_*.json` contains full real output, requests, provider response IDs, usage, attempts, source/matrix snapshots and Python validation. `requirement_comparison.csv` has 880 generated requirement-level comparisons. All ten plans cover the complete applicable matrix used for that role. A separate unfamiliar Word document tests a new role without reference fixture lookup.

The full role run deliberately uses unannotated source requirements after explicit automated fixture approval. It produces 880 visible warnings that free-form meaning and answer correctness need human review. Therefore 100% core coverage/traceability must not be described as fully verified teaching accuracy. Phase 3 separately tests structured conditions, exceptions, approved answer facts and repair. No role plan was assigned as real employee training in the user's main database.

## Capacity conditions and limits

The benchmark creates 1,000 employees, 100 roles, 1,000 document metadata records with representative source sections and requirements, and 1,000 one-module synthetic plans. It measures local HTTP route execution through TestClient, including templates and real MongoDB reads. The fixture does not measure production network latency, 1,000 concurrent sessions, full 88-module plans at scale, or worker saturation. Other local evaluation tasks were active. See capacity.json and capacity_before.json for all samples, environment, document parsing and database size.

The optimization removes duplicated current-matrix retrieval, caches per-role state only within each report request and narrows active-document checks to applicable requirement source IDs. It never caches generated answers or skips validation. Fifty existing/added tests passed after that change; the final expanded suite passes seventy.

## Security report

Authentication uses Argon2; request-time session expiry complements TTL cleanup. Tests exercise CSRF, permission groups, employee ownership, answer-key redaction, inactive/stale plans, malformed files, oversized archive expansion, macro rejection, quarantined source instructions, fake citations and missing mandatory content. Mocked API timeout, quota, authentication, invalid and refused-response paths verify bounded attempts and sanitized failures. These are application tests, not independent penetration-test certification.

## Remaining acceptance limits

Free-text semantic correctness, ambiguous distractors and equivalence of differently worded conditions still need review. The SRS difficulty-level field, full status vocabulary, reviewer override of blocking checks and dedicated aggregated role dashboard are not fully implemented as specified. CSV export exists; application PDF export does not. The 63-step acceptance matrix records these differences. The demo MP4 is an annotated replay; a continuous live-action demonstration and participant verification remain owner work. Public repository/blog publication remains separate; no artificial history or human signatures were created.
