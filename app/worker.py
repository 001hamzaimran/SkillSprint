from copy import deepcopy
import threading
from datetime import timedelta
from pymongo import ReturnDocument
from .db import now, uid, audit
from .generation import structured, GenerationFailure
from .schemas import Extraction, OnboardingPlan, FullOnboardingPlan
from .learning import learning_checks
from .ingestion import normalized, SUSPICIOUS
from .validation import validate_plan
from .policy import fingerprint, matrix, matrix_state, selective_delta


def enqueue(db, actor_id, kind, target_id, **job_context):
    job = {
        "_id": uid(),
        "kind": kind,
        "target_id": target_id,
        "actor_id": actor_id,
        "status": "queued",
        "created_at": now(),
        "attempts": [],
        "claims": 0,
        **job_context,
    }
    db.jobs.insert_one(job)
    audit(db, actor_id, "job.queued", job["_id"], {"kind": kind})
    return job


def process_one(db, settings, provider=structured):
    # A two-minute provider call plus one retry remains below this lease.
    claim_id = uid()
    job = db.jobs.find_one_and_update(
        {
            "claims": {"$lt": 3},
            "$or": [{"status": "queued"}, {"status": "running", "lease_until": {"$lt": now()}}],
        },
        {
            "$set": {
                "status": "running",
                "claim_id": claim_id,
                "lease_until": now() + timedelta(minutes=5),
                "started_at": now(),
            },
            "$inc": {"claims": 1},
        },
        sort=[("created_at", 1)],
        return_document=ReturnDocument.AFTER,
    )
    if not job:
        db.jobs.update_many(
            {"claims": {"$gte": 3}, "status": "running", "lease_until": {"$lt": now()}},
            {
                "$set": {
                    "status": "failed",
                    "error": "This job repeatedly lost its worker. Please retry.",
                    "finished_at": now(),
                }
            },
        )
        return False
    owned = {"_id": job["_id"], "claim_id": claim_id}

    def attempt(number, result):
        changed = db.jobs.update_one(
            owned,
            {
                "$set": {"lease_until": now() + timedelta(minutes=5)},
                "$push": {"attempts": {"number": number, "result": result, "time": now()}},
            },
        )
        if not changed.matched_count:
            raise GenerationFailure(
                "Worker ownership changed. This attempt cannot publish a result."
            )

    try:
        if job["kind"] == "extract":
            document = db.documents.find_one({"_id": job["target_id"]})
            if not document or document["suspicious"]:
                raise GenerationFailure(
                    "Document is missing or flagged for suspicious instructions."
                )
            sections = list(db.source_sections.find({"document_id": document["_id"]}))
            if sum(len(s["text"]) for s in sections) > 70000:
                raise GenerationFailure(
                    "AI extraction accepts up to 70,000 characters per document. Split this document first."
                )
            parsed, metadata = provider(
                settings,
                Extraction,
                "extract_v1.txt",
                {
                    "sections": [
                        {"section_id": s["section_id"], "text": s["text"]} for s in sections
                    ]
                },
                attempt,
            )
            saved = 0
            for req in parsed.requirements:
                section = next((s for s in sections if s["section_id"] == req.section_id), None)
                text = normalized(req.source_quote)
                if (
                    not section
                    or not text
                    or text not in normalized(section["text"])
                    or SUSPICIOUS.search(text)
                ):
                    continue
                if db.requirements.find_one(
                    {"document_id": document["_id"], "section_id": req.section_id, "text": text}
                ):
                    continue
                key = uid()
                db.requirements.insert_one(
                    {
                        "_id": key,
                        "requirement_id": "R-" + key[:12].upper(),
                        "document_id": document["_id"],
                        "section_id": req.section_id,
                        "title": req.title[:180],
                        "text": text,
                        "mandatory": req.mandatory,
                        "due_stage": req.due_stage,
                        "competency": req.competency[:180],
                        "role_ids": document["role_ids"],
                        "prerequisites": [],
                        "status": "draft",
                        "origin": "ai_extraction",
                        "created_at": now(),
                        "job_id": job["_id"],
                    }
                )
                saved += 1
            result_id = document["_id"]
            summary = f"{saved} new source-supported candidates added for review."
        else:
            employee = db.employees.find_one({"_id": job["target_id"]})
            if not employee:
                raise GenerationFailure("Employee no longer exists.")
            state = matrix_state(db, employee["role_id"])
            if state["unresolved"]:
                raise GenerationFailure(
                    "Resolve conflicting approved rules in Verification before generating this role plan."
                )
            requirements = state["requirements"]
            if not requirements:
                raise GenerationFailure(
                    "Approve source documents and applicable role requirements before generating a plan."
                )
            if len(requirements) > 120:
                raise GenerationFailure(
                    "This workspace supports up to 120 requirements per plan. Split larger role matrices into smaller learning tracks."
                )
            snapshot = fingerprint(requirements)
            employee_snapshot = {
                k: employee[k] for k in ("role_id", "department", "experience", "joining_date")
            }
            if (
                job.get("expected_snapshot", snapshot) != snapshot
                or job.get("expected_context", employee_snapshot) != employee_snapshot
                or job.get("expected_model", settings.genai_model) != settings.genai_model
            ):
                raise GenerationFailure(
                    "Controlled generation inputs changed. Start a new consistency experiment."
                )
            base, delta = None, None
            generate_requirements = requirements
            if job["kind"] == "selective":
                base = db.plans.find_one(
                    {"_id": job.get("base_plan_id"), "employee_id": employee["_id"]}
                )
                if (
                    not base
                    or not base.get("published_at")
                    or employee.get("active_plan_id") != base["_id"]
                    or base["role_id"] != employee["role_id"]
                ):
                    raise GenerationFailure(
                        "Selective updates require the currently assigned published version for this role."
                    )
                delta = selective_delta(base, requirements, employee_snapshot)
                generate_requirements = [
                    r for r in requirements if r["requirement_id"] in delta["regenerate"]
                ]

            allowed = [
                {
                    "requirement_id": r["requirement_id"],
                    "source_document_id": r["document_id"],
                    "source_section_id": r["section_id"],
                    "text": r["text"],
                    "title": r["title"],
                    "mandatory": r["mandatory"],
                    "due_stage": r["due_stage"],
                    "prerequisites": r["prerequisites"],
                    "policy_rule": r.get("policy_rule"),
                }
                for r in generate_requirements
            ]
            batches = []
            generated_items = (
                [
                    deepcopy(i)
                    for i in base["content"]["items"]
                    if i["requirement_id"] in delta["retained"]
                ]
                if base
                else []
            )
            first = None
            for offset in range(0, len(allowed), 4):
                attempt(0, "batch_" + str(offset // 4 + 1))
                chunk, record = provider(
                    settings,
                    FullOnboardingPlan,
                    "generate_v3.txt",
                    {"employee": employee_snapshot, "requirements": allowed[offset : offset + 4]},
                    attempt,
                )
                if chunk.role_id != employee["role_id"]:
                    raise GenerationFailure(
                        "Generated batch used the wrong role. No plan was published."
                    )
                first = first or chunk
                generated_items.extend(chunk.items)
                batches.append(record)
            # Keep old injected test providers supported, but incomplete plans cannot be published.
            schema = (
                FullOnboardingPlan
                if first is None or isinstance(first, FullOnboardingPlan)
                else OnboardingPlan
            )
            parsed = schema(
                title=base["content"]["title"] if base else first.title,
                summary=(
                    "Updated against the current approved policies. Unchanged modules are retained."
                    if base
                    else first.summary
                ),
                role_id=employee["role_id"],
                items=generated_items,
            )

            metadata = {
                "batches": batches,
                "model": settings.genai_model,
                "attempts": sum(b.get("attempts", 1) for b in batches),
            }
            document_ids = list({r["document_id"] for r in requirements})
            documents = list(db.documents.find({"_id": {"$in": document_ids}}))
            sections = list(db.source_sections.find({"document_id": {"$in": document_ids}}))
            validation = validate_plan(
                parsed, requirements, documents, sections, employee["role_id"]
            )
            repair_codes = {
                "STRUCTURED_RULE_MISMATCH",
                "CONDITION_OMITTED",
                "EXCEPTION_OMITTED",
                "QUIZ_ANSWER_FACT_MISMATCH",
                "QUIZ_EVIDENCE_MISMATCH",
            }
            repair_ids = {
                f.get("requirement_id") for f in validation["findings"] if f["code"] in repair_codes
            } & {r["requirement_id"] for r in allowed}
            if repair_ids:
                metadata["pre_repair_content"] = parsed.model_dump()
                metadata["initial_findings"] = validation["findings"]
                db.jobs.update_one(
                    owned,
                    {
                        "$set": {
                            "repair_evidence": {
                                "content": parsed.model_dump(),
                                "findings": validation["findings"],
                            }
                        }
                    },
                )
                repairs = []
                repair_inputs = [r for r in allowed if r["requirement_id"] in repair_ids]
                for offset in range(0, len(repair_inputs), 4):
                    attempt(0, "repair_batch_" + str(offset // 4 + 1))
                    repair_chunk = repair_inputs[offset : offset + 4]
                    revised, record = provider(
                        settings,
                        FullOnboardingPlan,
                        "generate_v3.txt",
                        {
                            "employee": employee_snapshot,
                            "requirements": repair_chunk,
                            "previous_items": [
                                i.model_dump()
                                for i in parsed.items
                                if i.requirement_id in {r["requirement_id"] for r in repair_chunk}
                            ],
                            "validation_findings": [
                                f
                                for f in validation["findings"]
                                if f.get("requirement_id")
                                in {r["requirement_id"] for r in repair_chunk}
                            ],
                            "repair_instructions": "Correct these exact Python findings. Copy answer_fact as the COMPLETE correct option, character for character (including case and punctuation). Put condition and exception excerpts in the lesson verbatim, including their punctuation. Return ONLY this batch of requirements.",
                        },
                        attempt,
                    )
                    if revised.role_id != employee["role_id"]:
                        raise GenerationFailure("Repair returned the wrong role.")
                    repairs.extend(revised.items)
                    record["repair"] = True
                    batches.append(record)
                parsed = FullOnboardingPlan(
                    title=parsed.title,
                    summary=parsed.summary,
                    role_id=parsed.role_id,
                    items=[i for i in parsed.items if i.requirement_id not in repair_ids] + repairs,
                )
                metadata["attempts"] = sum(b.get("attempts", 1) for b in batches)
                validation = validate_plan(
                    parsed, requirements, documents, sections, employee["role_id"]
                )
            teaching = learning_checks(parsed.model_dump())
            latest_employee = db.employees.find_one({"_id": employee["_id"]})
            stale = (
                snapshot != fingerprint(matrix(db, employee["role_id"]))
                or not latest_employee
                or any(latest_employee.get(k) != v for k, v in employee_snapshot.items())
            )
            if job.get("experiment_id") and stale:
                raise GenerationFailure(
                    "Inputs changed during the consistency run. Repeat with stable sources and employee context."
                )
            if stale:
                validation["core_passed"] = False
                validation["status"] = "Stale sources"
                validation["findings"].append(
                    {
                        "code": "MATRIX_CHANGED",
                        "message": "Approved requirements changed during generation. Regenerate the plan.",
                    }
                )
            # Stable job-derived result identity makes worker recovery idempotent.
            result_id = job["_id"]
            if not db.jobs.find_one({**owned, "lease_until": {"$gt": now()}}):
                raise GenerationFailure("Worker lease expired. This attempt cannot save a result.")
            db.plans.replace_one(
                {"_id": result_id},
                {
                    "_id": result_id,
                    "employee_id": employee["_id"],
                    "role_id": employee["role_id"],
                    "status": validation["status"],
                    "content": parsed.model_dump(),
                    "validation": validation,
                    "source_document_ids": document_ids,
                    "learning_checks": teaching,
                    "employee_snapshot": employee_snapshot,
                    "parent_plan_id": base["_id"] if base else None,
                    "origin": "selective_update" if base else "ai_generation",
                    "carry_parent_plan_id": base["_id"] if base else None,
                    "update_delta": delta,
                    "experiment_id": job.get("experiment_id"),
                    "matrix_snapshot": requirements,
                    "snapshot_digest": snapshot,
                    "created_at": now(),
                    "created_by": job["actor_id"],
                    "generation": metadata,
                    "prompt_version": "generate_v3",
                    "model": settings.genai_model,
                    "job_id": job["_id"],
                },
                upsert=True,
            )
            summary = (
                "Plan generated and independently checked. Read the findings before assignment."
            )
        db.jobs.update_one(
            owned,
            {
                "$set": {
                    "status": "completed",
                    "result_id": result_id,
                    "summary": summary,
                    "generation": metadata,
                    "finished_at": now(),
                }
            },
        )
        audit(db, job["actor_id"], "job.completed", job["_id"], {"result_id": result_id})
    except GenerationFailure as exc:
        db.jobs.update_one(
            owned, {"$set": {"status": "failed", "error": str(exc), "finished_at": now()}}
        )
    except Exception:
        # Do not leak provider responses, API keys or connection strings to UI/logs.
        db.jobs.update_one(
            owned,
            {
                "$set": {
                    "status": "failed",
                    "error": "Processing failed safely. Check document structure and retry; no content was approved.",
                    "finished_at": now(),
                }
            },
        )
    return True


def start_worker(db, settings):
    stop = threading.Event()

    def run():
        while not stop.is_set():
            try:
                if not process_one(db, settings):
                    stop.wait(1)
            except Exception:
                stop.wait(3)

    thread = threading.Thread(target=run, name="skillsprint-worker", daemon=True)
    thread.start()
    return stop, thread
