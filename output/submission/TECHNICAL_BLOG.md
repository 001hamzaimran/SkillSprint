# Building SkillSprint AI: onboarding that can show its evidence

Publication-ready draft for participant review. Not published. Written with AI assistance, as declared in AI_USAGE.md. The company and employees described here are fictional. This article reports a local competition implementation; deployment was removed from the requested scope.

## The business problem starts after the welcome email

An onboarding checklist often looks reassuring because it contains many tasks. That does not tell us whether it includes every mandatory policy, whether a task applies to the employee's role, or whether its instructions reflect the current policy version. A support employee and a warehouse employee can share information-security obligations while needing very different operational practice. When the source material changes, an administrator also needs to know which learning content and employee records are affected.

Generative AI makes it easy to produce a polished training plan. It does not automatically solve these control problems. A model can write an engaging lesson that quietly changes a deadline, cites an unrelated paragraph, or asks a quiz question whose answer cannot be justified from the company's documents. SkillSprint AI was built around that tension: use generation to make the learning useful, but keep the evidence, validation and approval decisions visible.

The fictional organization is AsterBridge Delivery Services. Its document pack contains policies, role procedures, historical versions, conflicting FAQs and adversarial examples. Choosing a coherent organization made the examples more useful than unrelated sample paragraphs. Delivery exceptions, access controls, refunds and customer escalation all produce concrete training obligations that an evaluator can inspect.

## A small Python architecture with explicit responsibilities

The local application uses FastAPI, Jinja2 templates, Pydantic and MongoDB. One Python service handles authentication, document workflows, review screens and learning. An embedded worker claims persisted generation jobs. Uploaded files live in a private directory, while MongoDB stores source locations, reviewed requirements, plans, attempts and audit events. The browser receives rendered pages with small amounts of JavaScript rather than a separate frontend application.

This structure was chosen for a solo competition project with a short deadline. It keeps installation and debugging manageable without placing every responsibility in one file. Ingestion, policy rules, generation, validation, learning, comparison and update handling have separate modules. The important boundary is conceptual: the component that generates a lesson is not the component that decides whether its requirement and source match.

MongoDB was a project requirement. Its document model fits bounded structures such as a learning item with a checklist, question and rubric. It does not mean all history should be embedded in one employee record. Quiz attempts, practical submissions, reviews and audit events grow independently, so they use separate collections. Unique indexes protect identities such as document/version and employee/login assignments. Required-field validators catch some invalid database writes before they become confusing UI failures.

## Documents become traceable sections before they become prompts

The upload workflow supports PDF and DOCX. A PDF section records its page and, when available, a numbered clause. A Word section records its paragraph or table-cell location. Longer content is split into bounded spans. These location identifiers are stored with the extracted text, so a reviewer can return from a generated item to the passage it claims to represent.

Parsing includes limits. The application checks file size, PDF headers, page counts, extracted text volume and the expanded size of Word archives. It rejects encrypted PDFs, unsupported formats, macro-bearing Word files and documents with no readable text. A scanned image therefore needs OCR before upload. Rejecting an unsupported input with an explanation is more honest than generating from an empty extraction and presenting the result as grounded learning.

Requirements start as drafts. For explicitly structured sample documents, clause extraction identifies candidate obligations. Unfamiliar documents can produce candidates from obligation language or through an optional AI extraction request. In both cases the candidate remains linked to its source passage. A reviewer must inspect the role scope, mandatory flag, training stage and wording before approval. Approving a source document and approving an extracted requirement are separate decisions.

## The role requirement matrix is an independent reference

The effective matrix contains approved requirements from active documents that apply to the selected role. It is assembled before the generation request. This ordering matters: retrieving a few similar passages after generation would not reveal a mandatory requirement that the model omitted entirely. The matrix supplies the expected set against which actual output is checked.

Each requirement has an identity, source document and section, exact passage, applicability, mandatory status and prerequisites. Reviewers can add structured policy annotations: a rule key, value, condition, exception, approved answer fact, module category and assessment topic. These annotations make selected claims independently checkable. They also expose an important limitation. Without reviewed structure, a matching quotation does not prove that every sentence in a generated explanation is correct.

The authored evaluation matrix contains 160 requirements across ten roles. Eighty requirements are common and eighty are role-specific, giving each role an 88-requirement complete matrix. The reference data helps run a reproducible evaluation, but its approval labels are explicitly fictional fixtures. The application does not use that reference file as an oracle for unknown documents uploaded by a judge.

## Prompt engineering is a contract, not an approval mechanism

The generation adapter calls the OpenAI Responses API using structured parsing. Pydantic describes the expected JSON: staged learning items with an objective, lesson, checklist, practical activity, scenario, multiple-choice question and scoring rubric. The prompt asks the model to copy requirement and source identities, preserve the approved quotation, respect mandatory flags and avoid inventing company deadlines or thresholds.

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

## Policy changes should preserve work that still applies

Activating a newer source marks affected plans stale. An impact preview identifies affected employees and learning components before the version switch. Selective regeneration compares the new matrix with the old plan snapshot, including dependency changes and employee context. Unchanged modules can be retained; changed requirements and affected dependents are regenerated.

Publication is the point where eligible progress moves to the new version. The application checks that a retained module is still identical and that the original plan remains the assigned published version. Copied records use deterministic identifiers and references to their original records, making retries safe. The original history is retained. Changed learning resets instead of inheriting a score that tested an obsolete rule.

A short employee write lease serializes publication and learner writes. This protects against a quiz being saved to the old version while a reviewer is copying its history to a new one. It is a focused concurrency safeguard for this workflow, not a claim that the entire application behaves like a multi-document transactional system.

## Evaluation must include the failures

The automated suite covers source parsing, permissions, review, quizzes, practical assessment, policy updates, selective carry-forward and comparison. Phase 4 added tests for all ten adversarial PDF fixtures, provider failure categories, unfamiliar Word tables, long-paragraph chunking and archive limits. The local suite passed seventy tests after the reporting optimization, with an upstream test-client deprecation warning documented separately.

Real generation evidence is stored apart from test doubles. The full ten-role evaluation uses the actual provider and complete 88-requirement matrices. Each role artifact includes the requests, structured output, validation and elapsed time. The comparison CSV contains requirement-level expected and actual results. Failed API calls or mismatches remain evidence; they are not replaced with invented success records.

A previous small live workflow tested two controlled generations and a selective policy update. Its tracked consistency score was 100 percent, and the update retained one module while regenerating another. The score demonstrates repeatability under those controlled inputs. It does not prove that generated explanations are true or that a larger benchmark will behave identically.

## A measured optimization was more useful than a performance promise

The local capacity fixture uses one thousand employees, one hundred roles, one thousand documents with representative source records, and one thousand synthetic one-module plans. This is a database and page-rendering experiment, not a simulation of one thousand simultaneous users. Three requests per route provide a small repeatable sample, and the report includes both the fixture shape and the measurements.

The full reports page initially took a median of about 20.9 seconds. Inspection showed repeated effective-matrix queries for employees sharing a role. Reusing each role's matrix within the same request and checking only applicable source identities reduced the median to about 3.1 seconds on the same local fixture. Filtered views were faster still. That is a concrete improvement with a reproducible mechanism, not a claim of production-scale performance.

Full plan generation remains much slower than the SRS thirty-second target. The first four 88-module runs took approximately six minutes each in the concurrent evaluation. Batching limits request size but does not remove the cost of producing hundreds of detailed learning fields. The final evidence therefore records the target as unmet rather than quoting a small request as if it represented the full workload.

## Security begins at the boundaries

Passwords use Argon2, sessions use random tokens with server-side expiry, and mutation forms require CSRF protection. Authorization is checked against both application roles and the employee record involved. Uploaded files remain private; their storage names are generated internally. Browser security headers constrain scripts and framing, and CSV exports escape formula-like cell values.

Prompt-injection detection quarantines known suspicious instructions, but a pattern detector is not the whole defense. Documents do not have tools, database credentials or authority to change roles and completion records. The model receives source data inside a constrained generation request. Independent validation calculates coverage from actual records. Adversarial tests check that uploaded instructions cannot activate themselves, queue generation through a quarantined source or alter user permissions.

Secrets remain in a local environment file excluded from packaging. Submission generation uses an explicit file allowlist rather than archiving the workspace indiscriminately. Private uploads, the virtual environment and local credentials are excluded. A final manifest hashes packaged files so the owner can inspect exactly what is being submitted.

## Lessons learned and the remaining boundaries

The most useful design decision was preserving distinctions: source approval versus requirement approval, schema validity versus factual support, validation versus publication, and publication versus employee completion. Combining these states would make the interface look simpler while making its claims less reliable. Keeping them explicit makes failures easier to explain to a reviewer and easier to test.

The local build still has limitations. Human interpretation remains necessary for free-form meaning and ambiguous applicability. Scanned documents need OCR before upload. Full generation misses the latency target. The capacity sample does not establish concurrency limits or general availability. Public deployment was deliberately removed from the current phase, and public repository/blog publication remains a separate owner action.

Future work should follow measured needs: pagination and bulk loading for large reports, carefully bounded generation parallelism, richer reviewed annotations, broader adversarial evaluation and stronger evaluation of ambiguous distractors. The participant must also read, adapt and understand the AI-assisted implementation before claiming it as independently verified work. A competition project is stronger when its evidence explains both what works and what remains uncertain.
