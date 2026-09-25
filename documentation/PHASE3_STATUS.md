# Phase 3: verification, policy updates and reports

Implemented locally on 2026-09-25. MongoDB remains the application database. Phase 4 remains for broader evaluation, performance, deployment and competition submission.

## Delivered

- Reviewed rule annotations with source-supported values, conditions, exceptions and quiz answer facts. Python independently checks these fields, source evidence and coverage. Unannotated requirements visibly require human interpretation.
- Explicit precedence decisions for conflicting rule keys in the same condition context. Decisions expire when their source snapshot changes. Unresolved conflicts block generation/publication. Missing prerequisites and dependency cycles are reported.
- Policy impact preview lists affected employees and learning components before activating a replacement source.
- Selective updates create a new plan version, regenerate changed requirements and their dependents, and retain unchanged modules. Reviewer publication copies only eligible unchanged learning, quiz and practical records. Changed modules restart. Original records remain intact; employee write leases serialize publication and learner changes.
- Side-by-side plan comparison and controlled two-run consistency experiments. Jaccard overlap measures requirements, source references, module categories and assessment topics. Changed inputs or human-edited versions do not receive a controlled aggregate score.
- Permission-scoped, searchable reports with role/status filters, CSV export and per-plan validation CSV. Spreadsheet formula-like values are escaped.
- One bounded AI repair pass for structured validation errors. Original output/findings are preserved in the job before the repair call and in successful plan metadata. Unfixed results remain blocked; an API outage fails safely.

## Walkthrough

1. Review source requirements in Knowledge library. Expand a requirement and enter reviewed rule annotations and prerequisite IDs; approve only exact source-supported facts.
2. Open Verification, choose a role and resolve any conflicting rules with a documented precedence reason.
3. Generate a plan and inspect the machine findings, lessons and answers. Use the controlled consistency action to generate two additional billable runs; inspect/export their comparison.
4. Upload a new policy version and select Preview policy impact before activation. Activate and review its new requirements.
5. On the employee’s currently assigned published plan, preview the selective update and queue regeneration. Review the new version before publication. Eligible unchanged progress is copied during publication.
6. Use Reports to filter employees/plans and export evidence.

## Verification evidence

- 33 automated tests passed in 34.81 seconds, including authorization, stale precedence, dependency cycles, selective regeneration, progress migration, write locks, controlled-input changes, CSV escaping and all three bounded repair outcomes. One upstream Starlette/httpx deprecation warning remains.
- Real OpenAI workflow passed in 44.24 seconds total: initial two-module generation, two controlled repeats, one-module policy update and publication-path checks. Tracked consistency was 100%; one module was retained, one regenerated, and one record from each learning collection was carried forward. The initial generation needed one repair. See reports/phase3_live_smoke.json.
- Earlier real runs failed validation and were not published; retained in reports/phase3_live_first_attempt.json and reports/phase3_live_second_attempt.json. The second failure involved a condition excerpt missing from a selective lesson; its full selective output was not captured in that early test script. The script now captures it before assertions.
- Browser smoke checks inspected Verification and Reports with an explicitly synthetic disposable workspace. Automated tests exercise impact, comparison, experiments and update endpoints.
- Live test approvals and seeded progress were synthetic integration fixtures, not human review or proof of employee competency. Test databases were isolated from the main workspace and removed.

## Limits and remaining work

These checks do not establish general semantic correctness. Differently worded conditions are not automatically equivalent; free-form lessons, distractors and practical responses require human review. Exact excerpt checks can reject correct paraphrases by design. Replacing an entire source conservatively regenerates its changed requirement identities. Consistency is repeatability, not correctness. The 44.24-second test covers several operations and is not a per-plan capacity benchmark; the SRS 30-second target remains unproven/unmet in earlier larger runs. Phase 4 must complete wider role/dataset evaluation, security and load evidence, deployment, demo materials and submission review. PDF report export is not implemented.
