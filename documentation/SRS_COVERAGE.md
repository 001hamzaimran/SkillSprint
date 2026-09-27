# SRS implementation and acceptance map

Updated 2026-09-27. This is a code/workflow map, not certification that every SRS requirement has passed acceptance. Automated tests use provider test doubles; live AI quality, hosted behavior, performance, capacity, and uptime need separate evidence. Historical evaluation reports predate this revision.

| SRS functional requirements | Implementation / acceptance boundary |
| --- | --- |
| i–ii Authentication and role access | Hashed passwords, expiring server sessions, CSRF, explicit roles; React login/recovery. Exact-origin protection added for API writes. |
| iii–iv Employee and role management | Create/link employee accounts and managers, edit profiles and roles under Manage; generation-context edits invalidate plans. |
| v–x Upload, validation, parsing, chunks, metadata, versions | PDF/DOCX ingestion, size/type/duplicate checks, source sections, activation and obsolete-version handling. Railway uploads require a volume. |
| xi–xii Extraction and role matrix | Draft source-quoted AI candidates; human approval, role scope, mandatory flag, classification and priority; Not Applicable excluded from generation. |
| xiii–xvi Provider, prompts, JSON, schema | OpenAI structured output, stored templates, Pydantic validation, prompt fingerprints and model/usage metadata. Live provider regression remains to run after these changes. |
| xvii–xviii Personalization and stages | Employee role, department, experience, joining date; admin-configured offsets for six stages, snapshotted on new plans. Arbitrary stage names are not supported. |
| xix–xxiii Modules, objectives, checklists, tasks, scenarios | Structured generated teaching items tied to approved requirements; editor/reviewer workflow. |
| xxiv–xxv Quiz generation and answer validation | Multiple choice, multiple response, true/false and scenario questions; exact-set multi-response scoring. Reviewed answer facts are checked deterministically; unannotated answer meaning requires human review. |
| xxvi–xxvii Assessment and rubrics | Practical/scenario submissions, criteria, 1–5 point weights, expected performance, 80% pass rule, reviewer/assigned-manager grading. |
| xxviii–xxix Prerequisites and sequence | Extraction suggests referenced source sections with exact dependency evidence; reviewers select approved requirement IDs. Validator checks unavailable dependencies, cycles and stage order. Suggestions do not auto-approve dependencies. |
| xxx–xxxiv Citations, independent validation, mandatory coverage, scores | Python validator has no AI approval call; compares source identity/version, matrix, required IDs and stage deadlines. Core failures block publication. |
| xxxv–xxxvii Unsupported claims, contradictions, precedence | Exact evidence checks, reviewed structured facts/conditions/exceptions, numeric-claim advisory, conflict groups and recorded reviewer-selected precedence. General semantic hallucination detection is not guaranteed. |
| xxxviii–xxxix Duplicates and relevance | Repeated questions, similar titles/tasks, repeated checklist advisories, role/matrix mismatch findings. Similarity is a heuristic requiring review. |
| xl–xliii Consistency, score, comparison, item status | Controlled repeated generation; requirement/source/category/topic overlap; explicit verification rows. Cross-profile comparisons do not receive an invalid consistency score. |
| xliv–xlvii Queue, decisions, overrides, audit | Review queue, edit/revalidate, approve/publish, reject/regenerate; reasoned advisory overrides preserve original findings. Overrides cannot bypass missing mandatory coverage or invalid sources. |
| xlviii–xlix Injection and adversarial detection | Uploaded content is treated as data; suspicious instructions are quarantined; adversarial fixtures exercise checks. Pattern matching is not a complete attack detector. |
| l–liii Employee/admin/role dashboards and tracking | My Sprint, plans, matrix, role insights; persistent lesson/checklist/quiz/submission progress. Learner API output recursively removes answer-key fields. |
| liv–lvi Progress, weak areas, recommendations | On Track / Behind Schedule / Assessment Required / Requires Attention / Completed; hourly persisted evaluation plus request-time insights. Recommendations derive from observed performance and overdue work, not invented completion. |
| lvii–lix Policy changes, impact, selective update | Version activation marks impacted plans; delta preview; only affected items regenerated, with eligible progress carry-forward after review. |
| lx Search/filter | Scoped employee, role, document and module search, department and status filters. |
| lxi–lxii Reports/exports | Coverage, source traceability, validation, learning/assessment reports; authorized CSV and JSON downloads proxied by Vercel. |
| lxiii–lxv Errors/retries/logging | Bounded provider retries, persisted job failures/attempts, explicit failed-job retry, model/template/hash metadata. Failed controlled experiments require a new paired run. |
| lxvi Responsive interface | React layouts and route guards; build verified. Full keyboard, mobile and browser acceptance remains to be completed. |

## Outstanding acceptance work

- Recorded verification: full regression run **80 passed** (1 deprecation warning, 1,241.62 seconds); after the final extraction/review changes, the focused SRS module **5 passed** (77.99 seconds). The final added prerequisite test was not part of the earlier full-suite collection. React TypeScript/Vite production build and ASGI import passed; Git whitespace checks passed. A single large JavaScript bundle warning remains.
- Rerun the whole suite after subsequent changes; live/hosted acceptance is separate from these local test-double results.
- Complete authenticated browser testing of every role and new workflow, including mobile and keyboard navigation.
- Run live AI tests with fictional documents after the schema/prompt changes, covering all quiz types and prerequisite suggestions. No new live-provider measurements are claimed here.
- Deploy and exercise both real domains, secure cookies through Vercel rewrites, SMTP reset delivery, persistent uploads after redeployment, backups and restore.
- The SRS **30-second generation target is not met by historical full-plan measurements**. Asynchronous jobs improve usability but do not satisfy that latency target.
- The PostgreSQL adapter still evaluates many filters in Python and uses table-level write locks. The SRS 1,000-employee/100-role/1,000-document capacity target needs a representative load test and likely indexed repository/query work.
- 99% uptime requires hosting operations and monitoring over time; it cannot be established by local tests.
- Competition submission requirements (genuine multi-day Git activity, published materials and participant verification) require real owner actions. No history, publication or sign-off has been fabricated.

Follow [DEPLOYMENT.md](DEPLOYMENT.md) for Railway and Vercel setup.
