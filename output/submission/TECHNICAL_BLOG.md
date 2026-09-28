# Building SkillSprint AI: An Onboarding App That Shows Its Evidence

How React, FastAPI, PostgreSQL, and independent Python validation turn company documents into reviewable learning plans.

A generated onboarding plan can sound convincing and still miss the one policy an employee must understand before starting work.

That is the problem behind SkillSprint AI. The goal is not simply to turn a PDF into a friendly checklist. It is to show which obligations belong in a plan, where the learning content came from, and what still needs a human decision.

> Generating training is one problem. Knowing whether it covers the right requirements is another.

## The business problem starts after the welcome email

An onboarding checklist often looks reassuring because it contains many tasks. That does not tell us whether it includes every mandatory policy, whether a task applies to the employee's role, or whether its instructions reflect the current policy version. A support employee and a warehouse employee can share information-security obligations while needing very different operational practice. When the source material changes, an administrator also needs to know which learning content and employee records are affected.

Generative AI makes it easy to produce a polished training plan. It does not automatically solve these control problems. A model can write an engaging lesson that quietly changes a deadline, cites an unrelated paragraph, or asks a quiz question whose answer cannot be justified from the company's documents. SkillSprint AI was built around that tension: use generation to make the learning useful, but keep the evidence, validation and approval decisions visible.

The fictional organization is AsterBridge Delivery Services. Its document pack contains policies, role procedures, historical versions, conflicting FAQs and adversarial examples. Choosing a coherent organization made the examples more useful than unrelated sample paragraphs. Delivery exceptions, access controls, refunds and customer escalation all produce concrete training obligations that an evaluator can inspect.

## The architecture: React in front, Python at the decision boundaries

The current application uses a React and TypeScript frontend built with Vite, a FastAPI backend, Pydantic schemas, and PostgreSQL. React provides the main workspace; the earlier Jinja2 interface remains available in the backend. The project has moved beyond the original MongoDB-backed, server-rendered implementation.

The backend handles authentication, document processing, generation jobs, review, assessment, and progress. An embedded worker claims persisted jobs, so the browser can show their status while generation continues. Ingestion, policy rules, generation, validation, learning, comparison, and update handling have separate modules.

PostgreSQL stores application records in JSONB-backed tables. Learning items contain structured checklists, questions, and rubrics, while attempts, submissions, reviews, and audit events have independent records. Original uploads remain in private file storage rather than being bundled into the frontend.

The important architectural boundary is not the choice of framework: the component that generates a lesson is not the component that decides whether its requirement and source match.

## Documents become traceable sections before they become prompts

The upload workflow supports PDF and DOCX. A PDF section records its page and, when available, a numbered clause. A Word section records its paragraph or table-cell location. Longer content is split into bounded spans. These location identifiers are stored with the extracted text, so a reviewer can return from a generated item to the passage it claims to represent.

Parsing includes limits. The application checks file size, PDF headers, page counts, extracted text volume and the expanded size of Word archives. It rejects encrypted PDFs, unsupported formats, macro-bearing Word files and documents with no readable text. A scanned image therefore needs OCR before upload. Rejecting an unsupported input with an explanation is more honest than generating from an empty extraction and presenting the result as grounded learning.

Requirements start as drafts. For explicitly structured sample documents, clause extraction identifies candidate obligations. Unfamiliar documents can produce candidates from obligation language or through an optional AI extraction request. In both cases the candidate remains linked to its source passage. A reviewer must inspect the role scope, mandatory flag, training stage and wording before approval. Approving a source document and approving an extracted requirement are separate decisions.

## The role requirement matrix is an independent reference

The effective matrix contains approved requirements from active documents that apply to the selected role. It is assembled before the generation request. This ordering matters: retrieving a few similar passages after generation would not reveal a mandatory requirement that the model omitted entirely. The matrix supplies the expected set against which actual output is checked.

Each requirement has an identity, source document and section, exact passage, applicability, mandatory status and prerequisites. Reviewers can add structured policy annotations: a rule key, value, condition, exception, approved answer fact, module category and assessment topic. These annotations make selected claims independently checkable. They also expose an important limitation. Without reviewed structure, a matching quotation does not prove that every sentence in a generated explanation is correct.

The authored evaluation matrix contains 160 requirements across ten roles. Eighty requirements are common and eighty are role-specific, giving each role an 88-requirement complete matrix. The reference data helps run a reproducible evaluation, but its approval labels are explicitly fictional fixtures. The application does not use that reference file as an oracle for unknown documents uploaded by a judge.

## Prompt engineering is a contract, not an approval mechanism

The generation adapter calls the OpenAI Responses API using structured parsing. Pydantic describes the expected JSON: staged learning items with an objective, lesson, checklist, practical activity, scenario, quiz, and scoring rubric. Supported quiz types include multiple choice, multiple response, true/false, and scenario-based questions. The prompt asks the model to copy requirement and source identities, preserve the approved quotation, respect mandatory flags, and avoid inventing company deadlines or thresholds.

Requirements are sent in bounded batches of four. That keeps individual requests reviewable and avoids depending on a single very large response. The worker assembles a complete plan after all batches finish. Model responses include provider metadata and usage information. Prompt versions remain as files, and the evaluation records prompt hashes so the tested instruction text can be identified precisely.

An early structured-rule test showed why exact contracts need examples. A model changed an approved answer from a bare duration into a prefixed phrase. Another output omitted the required exception excerpt from the lesson. These were real validation failures, not cases to hide by loosening the validator. The prompt now illustrates the exact answer contract and asks annotated lessons to include condition and exception lines before the explanatory prose.

## Bounded repair preserves the evidence of failure

There is one repair pass for a defined group of structured findings, including omitted conditions, mismatched rule facts and unsupported quiz evidence. The repair request contains the affected requirements, the previous items and the independent findings. It does not ask the model to decide whether its own work should be approved. The resulting items go through the same Python checks again.

Before the repair API call, the worker saves the first output and its findings in the job record. That detail is easy to overlook. If the provider becomes unavailable during repair, keeping evidence only in the final plan would lose the original output. Persisting it beforehand makes the failure inspectable even when no repaired plan can be saved.

Repair is bounded rather than an open-ended loop. If the model still fails, the result remains blocked. Authentication and quota failures receive explicit messages. Connection and timeout errors have a fixed retry limit. Tests use controlled provider doubles to verify successful repair, unsuccessful repair and outage paths without pretending those doubles are fresh model output.

## What Python verifies, and what it does not

The validator compares expected requirement identities with generated items, checks role and mandatory status, verifies source identity and exact source support, and detects missing or duplicate requirements. It checks that training stages meet due-stage constraints and that prerequisites are available without cycles. For annotated rules it compares structured values and requires approved condition and exception excerpts in the lesson.

Quiz checks include an in-range correct index, distinct options, exact evidence and, where annotated, an approved answer fact. That is useful protection against certain answer errors. It is not complete semantic validation of every distractor. Two differently worded options could still be defensible in an ambiguous question. Reviewers must inspect teaching content before publication, and practical responses require a human assessor.

Coverage counts valid applicable mandatory requirements, not simply the number of generated items. An item with the right identifier but an invalid source cannot inflate that score. Traceability measures valid supported source references. Learning completion is another measure entirely. A plan can have complete coverage while the employee has completed no training, and an employee's historic work can remain recorded while a policy update makes the assigned content stale.

## Contradictions need a context and a decision trail

A contradiction is not just two different numbers in two documents. The statements might apply under different conditions or to different roles. SkillSprint groups reviewed rules by a common key and normalized condition context, then compares values and exceptions. An unresolved group blocks generation for that effective matrix until a reviewer records which requirement takes precedence and why.

The precedence decision is tied to the conflict's snapshot. If a source rule changes, the old decision no longer silently resolves the new conflict. This is more conservative than assuming the newest uploaded FAQ overrides an authoritative policy. It also keeps the limitation clear: the system does not automatically infer that differently worded conditions mean the same thing, nor does it prove the absence of every semantic contradiction.

## Learning needs more than a generated checklist

The learner journey combines reading, checklist actions, a knowledge check and practical evidence. A module counts as complete only after all required components pass. Quiz attempts retain feedback. Practical submissions are graded against the rubric by an authorized reviewer or assigned manager. This prevents an AI-generated expected response from being mistaken for proof that an employee can perform the task.

The application separates permissions from business roles. An employee sees their own learning; a manager sees assigned employees; reviewers have review responsibilities. Unattempted employee responses exclude answer keys and expected scenario answers. Weak areas generate simple recommendations to revisit the policy evidence or use assessor feedback. These recommendations are intentionally understandable rather than unexplained personalization scores.

Administrators can configure day offsets for six onboarding stages. New plans retain a snapshot of that schedule, so changing the configuration does not silently move an existing employee's deadlines. Progress insights distinguish overdue learning, work awaiting assessment, and completed onboarding. A periodic evaluation stores progress summaries; the dashboard also calculates current insights when requested.

Requirement review now includes priority and classifications such as Must Know, Must Complete, and Must Demonstrate. Extraction can suggest prerequisites with supporting source passages, but a reviewer must confirm the actual requirement relationships. Suggested dependencies are not automatically promoted into approved policy.

The review queue brings flagged plans together. Authorized reviewers can record a reasoned override of an advisory recommendation while preserving the original finding. They cannot use that mechanism to bypass missing mandatory coverage or an invalid source.

## Policy changes should preserve work that still applies

Activating a newer source marks affected plans stale. An impact preview identifies affected employees and learning components before the version switch. Selective regeneration compares the new matrix with the old plan snapshot, including dependency changes and employee context. Unchanged modules can be retained; changed requirements and affected dependents are regenerated.

Publication is the point where eligible progress moves to the new version. The application checks that a retained module is still identical and that the original plan remains the assigned published version. Copied records use deterministic identifiers and references to their original records, making retries safe. The original history is retained. Changed learning resets instead of inheriting a score that tested an obsolete rule.

A short employee write lease serializes publication and learner writes. This protects against a quiz being saved to the old version while a reviewer is copying its history to a new one. It is a focused concurrency safeguard for this workflow, not a claim that the entire application behaves like a multi-document transactional system.

## Evaluation must include the failures

The automated suite covers source parsing, permissions, review, quizzes, practical assessment, policy updates, selective carry-forward, and comparison. It includes adversarial PDF fixtures, provider failure categories, unfamiliar Word tables, long-paragraph chunking, and archive limits.

The recorded full regression run passed 80 tests. A subsequent focused run passed five SRS tests after the final extraction and review changes. These are overlapping runs, not 85 unique tests. They use controlled provider doubles and do not establish live model quality. Later frontend changes passed the production build and a static navigation audit covering 80 link patterns against 32 registered routes. That audit checks route compatibility, not the existence of every record or every authenticated browser interaction.

Real generation evidence is stored apart from test doubles. The full ten-role evaluation uses the actual provider and complete 88-requirement matrices. Each role artifact includes the requests, structured output, validation and elapsed time. The comparison CSV contains requirement-level expected and actual results. Failed API calls or mismatches remain evidence; they are not replaced with invented success records.

A previous small live workflow tested two controlled generations and a selective policy update. Its tracked consistency score was 100 percent, and the update retained one module while regenerating another. The score demonstrates repeatability under those controlled inputs. It does not prove that generated explanations are true or that a larger benchmark will behave identically.

## A measured optimization was more useful than a performance promise

The local capacity fixture uses one thousand employees, one hundred roles, one thousand documents with representative source records, and one thousand synthetic one-module plans. This is a database and page-rendering experiment, not a simulation of one thousand simultaneous users. Three requests per route provide a small repeatable sample, and the report includes both the fixture shape and the measurements.

In the earlier implementation, the full reports page initially took a median of about 20.9 seconds. Inspection showed repeated effective-matrix queries for employees sharing a role. Reusing each role's matrix within the same request and checking only applicable source identities reduced the median to about 3.1 seconds on that local fixture. Those historical measurements predate the PostgreSQL migration; they are not benchmarks of the current hosted system.

Historical full-plan generation was much slower than the SRS thirty-second target: complete 88-module runs took roughly 333–484 seconds. Batching limits request size but does not remove the cost of producing hundreds of detailed learning fields. The target remains unmet in the recorded evidence. An asynchronous progress screen makes that wait more understandable; it does not make the generation itself faster.

## Deployment exposed bugs that a successful build did not

The deployment uses Vercel for the React frontend and Railway for the Python backend and PostgreSQL. Frontend requests use `/api`; Vercel rewrites forward those requests and authenticated downloads to Railway. Provider keys, database credentials, and mail credentials stay on the backend rather than in client-side Vite variables.

The split also makes file persistence important. A PostgreSQL volume does not preserve files uploaded to the backend's filesystem. Original documents need their own persistent storage, and a backup strategy must cover both the database and those originals. Password recovery similarly needs real SMTP delivery in production; development-only reset links are not a production substitute.

Deployment screenshots and user testing revealed a blank-page bug in several workspace screens. Those routes reused one React component with different modes. On navigation, React could retain data from the previous mode, while the next render expected a different response shape. Clearing the data inside an effect was too late: rendering could already have failed.

The fix was to give each mode its own keyed screen instance, cancel superseded data requests, and keep page-level errors inside a recovery boundary. The sidebar remains usable if a page fails. This was a useful reminder that TypeScript compilation is not an end-to-end navigation test, especially when response data is typed too loosely.

A second issue was simpler: the Overview button linked to `/requirements`, while the actual role-matrix route was `/matrix`. The button now uses the canonical route, and the old path redirects for existing bookmarks. The navigation audit was added to catch unresolved literal and templated destinations before deployment. Source-section anchors and post-login destinations were also corrected.

The sidebar was reorganized around the primary workflow: Overview and the core pages first, supporting tools next, and administration below. Consistent icons, a separately scrolling navigation area, and a collapsible mobile menu make the available actions easier to find.

These fixes are implemented in the project source. A passing build or route audit should not be confused with confirmation that every latest change has reached the live deployment. That still needs a deployment check and authenticated browser testing.

## Security begins at the boundaries

Passwords use Argon2, sessions use random tokens with server-side expiry, and mutation forms require CSRF protection. Authorization is checked against both application roles and the employee record involved. Uploaded files remain private; their storage names are generated internally. Browser security headers constrain scripts and framing, and CSV exports escape formula-like cell values.

Prompt-injection detection quarantines known suspicious instructions, but a pattern detector is not the whole defense. Documents do not have tools, database credentials or authority to change roles and completion records. The model receives source data inside a constrained generation request. Independent validation calculates coverage from actual records. Adversarial tests check that uploaded instructions cannot activate themselves, queue generation through a quarantined source or alter user permissions.

Local secrets belong in an excluded environment file; deployed secrets belong in the backend service's private configuration. Screenshots need the same care as source code: a settings screenshot can expose a credential even when the repository is clean. Any exposed credential must be revoked and replaced, not merely hidden in a later image.

Submission packaging uses an explicit file allowlist. Private uploads, local credentials, and development environments are excluded. Existing submission archives and hash manifests describe the versions they packaged; they must be regenerated if updated files are submitted.

## Lessons learned and the remaining boundaries

The most useful design decision was preserving distinctions: source approval versus requirement approval, schema validity versus factual support, validation versus publication, and publication versus employee completion. Combining these states would make the interface look simpler while making its claims less reliable. Keeping them explicit makes failures easier to explain to a reviewer and easier to test.

The application still has important limitations. Human interpretation remains necessary for free-form meaning and ambiguous applicability. Scanned documents need OCR before upload. Historical full generation misses the latency target. The current PostgreSQL adapter evaluates many filters in Python and uses table-level write locks, so representative load testing and query optimization remain necessary. Neither a local capacity fixture nor a live domain proves concurrency limits, backup reliability, or an uptime target.

The next work should follow measured needs: indexed queries and pagination, carefully bounded generation parallelism, live evaluation of the expanded quiz schema, broader adversarial testing, and authenticated browser checks across roles and screen sizes.

The central lesson is that a useful AI application needs more than a good prompt. It needs clear boundaries between generated content, approved evidence, human decisions, and recorded outcomes.

SkillSprint AI is built around those boundaries. Its strongest claim is not that AI makes onboarding automatically correct. It is that the system makes its evidence—and its remaining uncertainty—available for inspection.

---

*Disclosure: This project and article were developed with AI assistance. AsterBridge Delivery Services and the example company records are fictional. Test results refer to the recorded runs described above, not a claim of complete SRS acceptance or production certification.*
