# MongoDB implementation design

Status: the table below is the target architecture. The local Phase 1/2 implementation is connected to MongoDB and creates its collections/indexes in app/db.py. Current collections are users, sessions, login_limits, employees, job_roles, documents (one immutable version per record), source_sections, requirements, jobs, plans, audit_events, plan_reviews, learning_progress, quiz_attempts and practical_submissions. Plan content and matrix snapshots are embedded in each immutable plan version. Employee active_plan_id is the authoritative assignment pointer; progress and attempts refer to a specific plan ID. Unique indexes prevent multiple profiles per linked login, duplicate progress rows and simultaneous pending submissions for the same module.

Use FastAPI, PyMongo, Pydantic and a server-rendered Jinja2 interface. MongoDB is the sole application database. Use explicit UTC timestamps for storage and Asia/Karachi for the company display/calendar. Store stable business identifiers separately from MongoDB `_id` values so citations remain readable.

## Collection boundaries

| Collection | Main contents | Important indexes |
|---|---|---|
| users | Normalized login, password hash, authorization roles, active flag | Unique normalized login |
| sessions | Hash of random session token, user ID, expiry, revocation | Unique token hash; TTL expiry; user ID |
| employees | Role, department, manager, joining date, experience | Employee ID unique; manager and job role |
| job_roles | Configurable role name, scope and competencies | Unique company and role ID |
| documents | Logical document identity and current approved version pointer | Unique company and document ID |
| document_versions | Immutable metadata, effective interval, file reference and digest | Unique company/document/version; file digest; approval/effective date |
| source_sections | Version ID, section ID, text, PDF page or Word paragraph/table location | Unique version/section ID; version ID |
| requirements | Versioned requirement, applicability, structured facts, source links and prerequisites | Unique company/requirement/revision; role IDs; source version |
| matrix_snapshots | Frozen applicable requirement revisions and approval metadata | Company/role/created time |
| generation_jobs | Status, input reference, attempts, lease owner and lease expiry | Status/lease expiry; unique idempotency key |
| generation_runs | Actual provider/model, prompt version, source snapshot, timing and output reference | Job ID; created time |
| plan_versions | Employee, matrix snapshot, stage metadata, publication/verification states | Employee/created time; unique plan ID/version |
| learning_items | Module/task/checklist/question, bounded content and source links | Plan version; requirement IDs; source version/section |
| attempts | Learner answers, scored rubric, source/plan version | Employee/item/submitted time |
| completions | Completion evidence and effective item version | Unique employee/item/version |
| validation_runs | Expected/actual findings, scores and validator version | Plan version/created time |
| review_decisions | Reviewer, original finding reference, action and reason | Finding/created time |
| audit_events | Append-only actor/action/target/time and safe before/after references | Target/time; actor/time |

Indexes are to be created explicitly by an idempotent initialization command and tested for the deployed query patterns. TTL expiration is cleanup, not authorization: the server must reject an expired session immediately even if its record has not yet been removed.

## Schema and publication controls

- Validate input with Pydantic and stored documents with collection JSON Schema validators. Require types, version references, timestamps and allowed states.
- Validate relationships in application services; MongoDB does not supply relational foreign-key enforcement for these references.
- Keep original uploads in private storage with a digest and authorized download route, or use GridFS. Metadata belongs in MongoDB either way. Never put unbounded file bytes inside a plan record.
- Keep growing event histories and learning items in separate collections. Embed only bounded data such as quiz options, a rubric and source links for one item.
- Freeze source and matrix snapshots when generation begins. Compare the active source pointer again before publishing so a concurrent policy update cannot silently publish stale training.
- Atomically claim jobs and update plan lifecycle fields. Use idempotency keys for results and retries. If multi-document transactions are used, verify deployment topology support first.
- Never pass user-provided MongoDB operators directly into filters or updates. Build allowed queries from validated fields.
- Apply server-side authorization to every document, employee, plan, report and review action. A job role such as Finance Associate is not an application administrator role.
- Hash passwords with a maintained password-hashing library; use expiring random sessions, CSRF defenses and rate limits. Store database credentials and GenAI keys in environment configuration, not in sample JSON or Git.

## Reference fixtures

The JSON under `sample_documents/asterbridge/reference` is an authored evaluation fixture. `requirements.json` contains source-linked reference requirements, not AI-generated plans. The application must derive candidates from uploads and approve them through its actual workflow. Hidden documents and new roles must use the same pipeline without code edits or hard-coded fixture lookup.

## Sources

- [Official PyMongo documentation](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/)
- [MongoDB schema validation](https://www.mongodb.com/docs/manual/core/schema-validation/)
- [FastAPI templates](https://fastapi.tiangolo.com/advanced/templates/)

## Phase 3 implementation additions

`conflict_resolutions` stores role/snapshot-scoped precedence decisions and reviewer reasons. `consistency_experiments` references two queued jobs and controlled input snapshots. Plans embed reviewed matrix snapshots, employee context, update deltas and generation/repair metadata. Jobs retain original repair evidence even if the provider fails. Employee records hold short-lived write locks; copied learning records use deterministic IDs and reference their original plan/record for retry-safe migration. MongoDB remains the sole application database.
