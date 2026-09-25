# SkillSprint AI: solo competition implementation plan

Planning basis: the complete 52-page SRS, version 1.0. The participant is working alone, has only three days remaining, and requires MongoDB. Updated 2026-09-25. Existing technical skills, API budget and deployment access remain unknown. Phases 1–3 are implemented locally; see documentation/PHASE3_STATUS.md for verified scope and remaining work. The roadmap below is not a claim of full SRS compliance.

## Product direction

Build a source-grounded onboarding application in which an evaluator can inspect any learning item, its source, the expected requirement, and the independent validation result. The central demonstration is: upload documents, generate a role-specific plan, expose an error, update a policy, and show exactly what must change.

Prioritize complete SRS coverage and an understandable Python implementation. Three days is a high-risk deadline for the complete SRS, especially with one developer; optional enhancements must not displace mandatory functionality or submission evidence. Build one end-to-end path early, keep the interface compact, and track incomplete requirements explicitly. The original SRS still asks for meaningful commits across five competition days: preserve genuine existing history and commit throughout the remaining days; never backdate or fabricate missing activity.

## Mandatory scope and evidence

| Workstream | Required implementation | Evidence of completion |
|---|---|---|
| Access | Login; administrator, training manager, reviewer, manager and employee permissions; employee profiles and configurable job roles | Authorization tests, including access to another employee's records |
| Documents | PDF and DOCX uploads; file validation; duplicate and empty detection; metadata, sections, chunks, dates, active and superseded versions | Both formats processed with reproducible source locations |
| Requirements | Source-linked role matrix; mandatory/optional classification, competencies, conditions, exceptions, deadlines and prerequisites | Reviewable matrix derived independently of generated plans |
| Generation | Actual GenAI API; versioned prompts; structured JSON; stages, modules, objectives, checklists, practical tasks, scenarios, quizzes and rubrics | Real requests/responses and complete plans for 10 roles |
| Validation | Schema, coverage, traceability, role relevance, unsupported claims, conflicts, versions, duplicates, prerequisites, quiz answers and assessment coverage | Python results with machine-readable reasons; at least 100 requirement-level comparisons |
| Consistency | Repeated controlled generations compared by requirement, source, module category and assessment topic | Stored comparison and calculated consistency score |
| Review | Approve, reject, edit, regenerate, comment and override | Original result and reviewer decision both preserved; edits revalidated |
| Learning | Employee, administrator and role dashboards; completion, quiz/assessment results, milestones, progress status, weak areas and recommendations | Complete learner journey with persisted progress |
| Updates | Detect affected employees, modules, checklists, tasks and quizzes; compare plans and selectively regenerate | Version-update demonstration preserving unaffected work |
| Reporting | Search, filters, progress/coverage/traceability/validation reports and export | CSV export and saved validation report; add PDF export if feasible |
| Reliability | Timeouts, bounded retries, quota handling, job status, secret protection, audit events and prompt-injection defenses | Failure and security tests; genuine failure states |

Dataset minimums: 20 company documents, 10 roles, 150 identifiable requirements, 50 mandatory requirements, 30 role-specific requirements, 10 conflicting or ambiguous cases, 10 policy-version changes, and 10 adversarial cases. Track each threshold explicitly in a dataset manifest rather than assuming the counts.

Performance targets from the SRS: standard plan generation and validation within 30 seconds under normal conditions; capacity for 1,000 employees, 100 roles and 1,000 documents without architectural redesign; 99% availability under the stated normal conditions. These must be measured, not claimed from the design alone.

## Proposed solo-friendly stack

- Python and FastAPI for a single application. PyMongo is the database driver. Use separate modules for ingestion, requirements, generation, validation, learning and review so the two pipelines remain independently understandable.
- Jinja2 templates, custom CSS and small JavaScript components for a responsive custom interface. Keep frontend and backend in one deployment for the three-day build.
- MongoDB is the only application database, with local MongoDB or an existing Atlas deployment selected according to available access. Keep document metadata and application state in collections; store original files in private storage with references, or GridFS if database-backed file storage is needed. Do not place whole PDFs or unbounded audit histories inside a plan document.
- Authentication must include password hashing, expiring server-side sessions, HTTP-only secure cookies in deployment, CSRF protection for mutations, and explicit permission and employee-record checks. FastAPI does not supply a complete user management application automatically; budget time for this work.
- pypdf/pdfplumber for PDFs and python-docx for DOCX. Preserve pages for PDF and paragraph/table-cell references for Word. Detect textless scans and report unsupported extraction clearly; OCR is a stretch feature unless evaluation requires it.
- Pydantic schemas for generated JSON, plus separate pure-Python business validation. Schema validity is not factual validity.
- One competition-approved GenAI provider, selected after a small real-document quality/latency/cost benchmark. Keep a provider adapter so the application is not coupled to model-specific output handling.
- A persisted generation_jobs collection and a separate Python worker process. UI polls status; workers atomically claim jobs with a lease, jobs have bounded retries, and result writes use idempotency keys. Recover expired leases without duplicating plan publication.
- Versioned configuration and prompts; Python tests for validation and browser smoke tests for the critical user journey.

Use Pydantic validation at application boundaries and MongoDB collection validators for required stored fields. Maintain unique compound indexes for document/version and requirement/version identities, indexed employee assignments and source dependencies, and an expiring session index. Reference checks and lifecycle rules remain explicit application responsibilities. Source snapshots are immutable; use single-document atomic state transitions and idempotent writes for publication, and only use multi-document transactions when the chosen MongoDB deployment supports them.

References: official PyMongo driver https://www.mongodb.com/docs/languages/python/pymongo-driver/current/ ; MongoDB schema validation https://www.mongodb.com/docs/manual/core/schema-validation/ ; FastAPI templates https://fastapi.tiangolo.com/advanced/templates/ ; Pydantic https://pydantic.dev/docs/validation/latest/get-started/ . Installed Phase 1 dependencies are pinned in requirements-lock.txt.

The SRS names Docebo as a conceptual reference. Its learning paths, skills and learning analytics are useful product references, while the original SkillSprint design should emphasize inspectable validation. Reference: https://www.docebo.com/ .

## Data flow and validation design

1. Validate and parse uploaded files; store immutable document versions and source spans.
2. Extract candidate requirements from the documents, independently of plan generation. Store actor, action, object, obligation, condition, exception, deadline, competency and evidence span. GenAI may assist interpretation but cannot certify its own extraction.
3. Deterministic checks validate source spans and supported structured facts. Explicitly flag ambiguous extraction, competing authority or unclear applicability. Human approval creates a versioned authoritative matrix where required; never automatically promote an AI draft to trusted ground truth.
4. Select all applicable mandatory matrix requirements before retrieving supporting passages. Similarity search must not accidentally omit mandatory requirements. Add relevant optional material within a bounded context budget.
5. Generate a JSON plan linked to requirement IDs, versioned sources and structured factual assertions.
6. Run the independent Python validator with no GenAI approval calls. Compare against the approved matrix snapshot and document metadata.
7. Show per-item expected versus actual results. Publish only after required checks pass, with distinct reviewer approval and machine verification states.
8. Store generation metadata, validation snapshot and source dependencies for later updates.

MongoDB collections: users, sessions, employees, job_roles, documents, document_versions, source_sections, requirements, matrix_snapshots, generation_jobs, generation_runs, plan_versions, learning_items, attempts, completions, validation_runs, review_decisions and audit_events. Embed bounded rubric, question-option, prerequisite and source-link structures with their owning record; store growing histories and learning items separately. Keep job roles distinct from application authorization roles. See documentation/MONGODB_DESIGN.md for the proposed indexes and boundaries.

The validator will check sets of applicable requirement IDs, role and condition applicability, source/version references, structured rule values, duplicate IDs/content, assessment-topic coverage and prerequisite order. Represent dependency order as a directed graph and detect cycles. For contradictions, compare normalized values, prohibitions, conditions and exceptions; apply configurable authority and effective-date rules. A newer FAQ must not automatically defeat an authoritative policy.

A citation proves location, not that a sentence follows from the source. Restrict company-specific factual content to verifiable structured assertions and supporting excerpts. Treat uncheckable free-text claims as needing review. General semantic contradiction detection cannot honestly be guaranteed with regex or source IDs alone. Quiz answer checks use approved facts and constraints; ambiguous distractors and free-form practical responses require review.

Coverage = unique covered applicable mandatory requirements / applicable mandatory requirements * 100. An item counts as covered only when its required content and checks pass. If the denominator is zero, display N/A rather than fabricated 100%. Traceability reports identify their exact denominator. Repeated-generation consistency uses set overlap of structured tuples and reports individual categories as well as an aggregate.

Final Verified requires complete applicable mandatory coverage, valid support, and no unresolved blocking findings. Reviewer override is separately labeled and never rewrites the original machine result. A new active policy can make a previously verified plan stale; preserve its history and issue a new plan version after revalidation.

For unseen documents and roles, use the same configurable pipeline with no code changes or manual patching of generated outputs. Automatically process clear cases; route unresolved cases through the application's visible review workflow. Document extraction limitations so a review flag is not presented as automatic factual understanding.

## Interface

Keep five main areas with role-specific navigation:

1. Overview: actual completion, coverage, overdue work and review counts; distinguish learning completion from content verification.
2. Knowledge Library: documents, extraction preview, versions, sources and role matrix.
3. Plan Builder: employee/role selection, stage timeline, generation job and plan comparison.
4. Verification Center: expected/actual/source comparison, finding details, review actions and audit history.
5. My Sprint: today's activities, readable modules, quizzes, practical submissions, milestones and weak-area practice.

Use consistent typography, restrained color, readable tables, keyboard-accessible controls, helpful empty states, loading feedback and recoverable errors. A source drawer should open without losing the current plan position. Keep developer diagnostics behind reviewer/evaluator views.

## Competition enhancements, ranked

| Enhancement | What is extra beyond the SRS | Priority |
|---|---|---|
| Evidence Explorer | Click any claim to open highlighted evidence, structured expected/actual values and the precise rule that passed or failed | First: builds on required traceability |
| Policy Change Preview | Before activating a revision, preview changes and affected learners, then compare old/new training side by side | Second: extends required update/impact handling |
| Evaluation Workbench | Run a supplied test pack, display actual results and export an evidence bundle with timestamps, source versions and failures | Third: extends required tests and reports |
| Workload-aware scheduling | Respect daily training minutes, prerequisites and mandatory deadlines; explain impossible schedules | Stretch after complete core |
| Spaced revision | Schedule source-linked follow-up questions from missed competencies and invalidate obsolete questions | Stretch beyond basic adaptive recommendations |
| Branching scenario practice | Learner choices lead to approved process branches with source-backed debriefs | Later; basic scenarios are already required |

For the three-day deadline, implement only a simple evidence drawer as part of required traceability. Defer the remaining optional enhancements until all mandatory acceptance checks and submission artifacts pass. Basic policy impact, selective regeneration, adaptive recommendations and scenarios remain required; their optional richer presentations are what is deferred. Voice avatars, social feeds, HRMS/payroll integration, complex badges and a general chatbot are outside the three-day plan.

## Fictional company pack

Created scenario: AsterBridge Delivery Services, a fictional delivery and merchant-support company. Roles: Customer Support Executive, Dispatch Coordinator, Warehouse Associate, Returns Specialist, Merchant Success Executive, Finance Associate, HR Executive, IT Support Engineer, Data Analyst and Operations Manager.

This scenario naturally supports escalation deadlines, refund approvals, delivery exceptions, data-access permissions and different onboarding tasks. Create original fictional business policies; do not imply they are legal guidance or real-company rules.

The authored pack is in sample_documents/asterbridge: 20 current PDF documents with editable Markdown, 160 identifiable requirements (140 mandatory and 80 role-specific), 10 earlier policy versions, 10 conflicting FAQ cases, 10 adversarial cases and JSON reference fixtures. The ten SOPs include role mandates and responsibilities. The current reading manual and portable ZIP are under output/company_pack. Human content review is pending; fixture approval labels describe the fictional scenario. Do not import the reference matrix as trusted output for unseen documents.

The pack is PDF-first. DOCX ingestion and source-location handling remain mandatory and must be tested using Word inputs during Day 1; PDF QA does not establish DOCX support. Prepare a separately held-out pack with unfamiliar wording and tables before final rehearsal.

## Three-day execution target

| Day | Main work | Exit criterion |
|---|---|---|
| 1 | FastAPI shell, MongoDB collections/indexes, authentication and permissions, employee/role forms, PDF/DOCX ingestion, source viewer, matrix extraction/review, real GenAI generation and core validation; deploy the shell early | A real uploaded document produces a role plan; sources resolve; missing mandatory content fails; both formats and the database persist across restart |
| 2 | Remaining validators, conflict/version rules, prerequisites, repeated-generation comparison, quizzes/rubrics, review/audit, employee progress and weak-area recommendations, policy impact and selective regeneration, search and CSV reports | Ten role plans work; reviewer and learner workflows persist; an updated policy invalidates affected items; 100+ actual comparison results are collected |
| 3 | Feature freeze; unseen documents and role tests, all adversarial cases, authorization and API failure tests, performance/capacity checks, deployment repairs, evidence collection, final report, MP4 and 2,000-word blog packaging | Critical failures repaired; final checklist accurately marks every requirement; public app and required artifacts ready; participant can explain and modify the core code |

Write documentation, AI_USAGE.md and meaningful Git commits every day. Draft the report and blog as modules are finished; the final day is packaging and repairs. Reserve at least the final third of Day 3 for deployment verification, video and submission checks. Keep a requirement-to-test-to-evidence checklist covering all 63 numbered functional requirements, non-functional requirements and integrity/deliverable clauses. If behind schedule, drop optional enhancements and simplify screen presentation; do not silently label missing SRS features complete. This target is not a guarantee that the complete SRS fits into three solo days.

## Acceptance and risk checks

- Real end-to-end tests for both document formats, all permission groups, source navigation, quiz attempts, review decisions and policy regeneration.
- Deliberate defects: missing mandatory requirement, irrelevant role task, unsupported topic, nonexistent citation, superseded policy, conflicting deadline, duplicated question, prerequisite violation and invalid JSON.
- All 10 adversarial cases exercise instruction isolation and access boundaries. Suspicious-text detection alone is not protection: documents cannot grant permissions, invoke tools or approve plans.
- Job failures: timeout, quota failure, partial response, retry exhaustion and repeated request. No fake success responses or cached responses presented as fresh API calls.
- Benchmark a defined standard plan after ingestion, report repeated timings and failures, and measure ingestion separately. Retries that exceed 30 seconds must remain visible. Cache parsing/requirements using source and prompt versions; do not use caching to conceal generation performance.
- Seed 1,000 employees, 100 roles and 1,000 document records plus representative content for capacity tests. Measure query time, memory and worker throughput; record dataset size and conditions.
- Monitor actual availability during the observation window. A brief demo does not prove a general 99% uptime guarantee.
- Deploy web process, worker, database and persistent private file storage; keep keys in environment variables; test a clean installation and evaluator accounts. Provide real previously generated plans for browsing during an outage with explicit timestamps, while new generation reports the outage honestly.

## Submission inventory

Project report including architecture, database and required diagrams; public GitHub repository with genuine daily history; source, dependency file and license; original dataset and matrix; prompts and schemas; generation requests/responses and retries; independent validation evidence; 100+ comparison results; complete plans for 10 roles; validation and security reports; test cases; setup/execution instructions; public application and evaluator access; mandatory MP4; published technical blog of at least 2,000 words; AI_USAGE.md; solo contribution record.

Record this planning assistance in AI_USAGE.md when establishing the project log. Mark human review as pending until the participant actually reviews it; never invent a verifying team member or completed tests.

## Demonstration story

Upload a policy and SOP, generate a Customer Support plan, and open a learning item in the Evidence Explorer. Show a controlled test with a missing requirement and its genuine failure result. Introduce a revised escalation deadline and show the affected tasks and questions. Regenerate affected content while preserving unrelated progress. Process an unfamiliar role and a malicious document. End with a real exported comparison report and employee learning progress. Keep the short live story focused; the mandatory video must cover the full SRS demonstration checklist.

## Current four-phase delivery grouping

1. Foundation and source-to-plan workflow: complete locally.
2. Learning, review and assessment: complete locally; see documentation/PHASE2_STATUS.md.
3. Advanced verification, consistency, selective policy updates and reporting: complete locally.
4. Local competition evaluation, performance optimization and submission packaging: delivered; owner publication/verification actions remain. Deployment removed by the user on 2026-09-25.

These phases group work within the original three-day target; they are not four separate calendar days. The Phase 2 live generation took 115.13 seconds, so the 30-second SRS target remains unmet.

## Scope amendment: 2026-09-25

The user explicitly removed deployment from Phase 4. Public hosting, cloud configuration and deployed evaluator accounts are excluded from this delivery. References to deployment above preserve the original SRS and planning history; they are not current tasks. Local evidence and submission artifacts are prepared here. Publishing to GitHub or a blog platform and participant human verification remain separate external/owner actions. The source SRS has 63 numbered functional steps, not the earlier planning count of 66.
