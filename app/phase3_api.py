"""Verification, impact analysis, experiments, and reports JSON API endpoints."""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from .db import now, uid, audit
from .security import require, EDITORS, REVIEWERS
from .schemas import PolicyRule
from .ingestion import normalized
from .policy import matrix_state, fingerprint, selective_delta, dependency_findings
from .worker import enqueue
from .learning import progress_report, public_content
from .comparison import compare_plans
from .api import _ser, ok, api_csrf, _text, _employee_access, _plan_access, _employees_for
from .training_api import _current

import re

router = APIRouter(prefix="/api")


# ── Verification ──────────────────────────────────────────────────────────────

@router.get("/verification")
def verification(request: Request):
    require(request, EDITORS | REVIEWERS)
    db = request.app.state.db
    roles = list(db.job_roles.find().sort("name", 1))
    role_id = request.query_params.get("role_id", roles[0]["_id"] if roles else "")
    state = matrix_state(db, role_id)
    return ok({
        "roles": roles,
        "role_id": role_id,
        "state": state,
        "dependencies": dependency_findings(state["requirements"]),
        "annotated": sum(bool(r.get("policy_rule")) for r in state["requirements"]),
    })


# ── Rule annotation ──────────────────────────────────────────────────────────

@router.post("/requirements/{requirement_id}/rules")
async def annotate_rules(request: Request, requirement_id: str):
    user, session = require(request, REVIEWERS)
    body = await request.json()
    api_csrf(request, session)
    db = request.app.state.db
    req = db.requirements.find_one({"_id": requirement_id})
    if not req:
        raise HTTPException(404, "Requirement not found.")
    key = str(body.get("key", "")).strip().lower()
    rule = None
    if key:
        if not re.fullmatch(r"[a-z0-9_.-]{2,80}", key):
            raise HTTPException(422, "Rule key must use 2-80 lowercase letters, numbers, periods, underscores or hyphens.")
        fields = {
            k: str(body.get(k, "")).strip()
            for k in ("value", "condition", "exception", "answer_fact", "module_category", "assessment_topic")
        }
        try:
            rule = PolicyRule(key=key, **fields).model_dump()
        except ValidationError:
            raise HTTPException(422, "Provide a rule value, module category and assessment topic.") from None
        for field in ("value", "condition", "exception", "answer_fact"):
            if rule[field] and normalized(rule[field]) not in normalized(req["text"]):
                raise HTTPException(
                    422,
                    f'{field.replace("_"," ").capitalize()} must be an exact excerpt of the approved requirement text.',
                )
    deps = list(
        dict.fromkeys(x.strip() for x in str(body.get("prerequisites", "")).split(",") if x.strip())
    )
    if len(deps) > 20 or req["requirement_id"] in deps:
        raise HTTPException(422, "Choose at most 20 prerequisites, excluding this requirement itself.")
    if db.requirements.count_documents(
        {"requirement_id": {"$in": deps}, "status": "approved"}
    ) != len(deps):
        raise HTTPException(422, "Prerequisites must reference existing approved requirement IDs.")
    reason = _text(body.get("reason", ""), "Review reason", 2000)
    db.requirements.update_one(
        {"_id": req["_id"]},
        {"$set": {
            "policy_rule": rule,
            "prerequisites": deps,
            "rules_reviewed_by": user["_id"],
            "rules_reviewed_at": now(),
        }},
    )
    db.plans.update_many(
        {"source_document_ids": req["document_id"]}, {"$set": {"status": "Stale sources"}}
    )
    audit(db, user["_id"], "requirement.rules", req["_id"],
          {"before": req.get("policy_rule"), "after": rule, "prerequisites": deps, "reason": reason})
    return JSONResponse(None, status_code=204)


# ── Conflict resolution ──────────────────────────────────────────────────────

class ResolveBody(BaseModel):
    conflict_id: str
    winner_id: str
    reason: str


@router.post("/verification/{role_id}/resolve")
def resolve_conflict(request: Request, role_id: str, body: ResolveBody):
    user, session = require(request, REVIEWERS)
    api_csrf(request, session)
    db = request.app.state.db
    group = next(
        (g for g in matrix_state(db, role_id)["conflicts"] if g["_id"] == body.conflict_id), None
    )
    if not group or body.winner_id not in {r["requirement_id"] for r in group["requirements"]}:
        raise HTTPException(409, "The conflict changed. Refresh and review.")
    reason = _text(body.reason, "Precedence reason", 2000)
    record = {
        "_id": body.conflict_id,
        "role_id": role_id,
        "winner_id": body.winner_id,
        "reason": reason,
        "actor_id": user["_id"],
        "created_at": now(),
    }
    db.conflict_resolutions.replace_one({"_id": body.conflict_id}, record, upsert=True)
    db.plans.update_many({"role_id": role_id}, {"$set": {"status": "Stale sources"}})
    audit(db, user["_id"], "policy.resolve", body.conflict_id, record)
    return JSONResponse(None, status_code=204)


# ── Impact analysis ──────────────────────────────────────────────────────────

@router.get("/documents/{document_id}/impact")
def document_impact(request: Request, document_id: str):
    require(request, EDITORS | REVIEWERS)
    db = request.app.state.db
    document = db.documents.find_one({"_id": document_id})
    if not document:
        raise HTTPException(404, "Document not found.")
    previous = list(db.documents.find({
        "document_id": document["document_id"],
        "status": "active",
        "_id": {"$ne": document_id},
    }))
    oldids = [d["_id"] for d in previous]
    affected = []
    for employee in db.employees.find({"active_plan_id": {"$exists": True}}):
        plan = db.plans.find_one(
            {"_id": employee["active_plan_id"], "source_document_ids": {"$in": oldids}}
        )
        if plan:
            keys = {
                i["requirement_id"]
                for i in plan["content"]["items"]
                if i["source_document_id"] in oldids
            }
            while True:
                expanded = keys | {
                    r["requirement_id"]
                    for r in plan.get("matrix_snapshot", [])
                    if any(d in keys for d in r.get("prerequisites", []))
                }
                if expanded == keys:
                    break
                keys = expanded
            items = [i for i in plan["content"]["items"] if i["requirement_id"] in keys]
            affected.append({
                "employee": employee,
                "plan": plan,
                "items": items,
                "checklists": sum(len(i.get("checklist", [])) for i in items),
                "quizzes": sum(bool(i.get("quiz")) for i in items),
            })
    return ok({
        "document": document,
        "previous": previous,
        "affected": affected,
        "old_requirements": list(db.requirements.find({"document_id": {"$in": oldids}})),
        "new_requirements": list(db.requirements.find({"document_id": document_id})),
    })


# ── Selective update ─────────────────────────────────────────────────────────

@router.get("/plans/{plan_id}/update")
def update_preview(request: Request, plan_id: str):
    require(request, EDITORS | REVIEWERS)
    plan = _plan_access(request, plan_id)
    db = request.app.state.db
    employee = db.employees.find_one({"_id": plan["employee_id"]})
    state = matrix_state(db, employee["role_id"])
    delta = selective_delta(
        plan, state["requirements"],
        {k: employee[k] for k in ("role_id", "department", "experience", "joining_date")},
    )
    return ok({
        "plan": plan,
        "delta": delta,
        "state": state,
        "employee": employee,
        "old": {r["requirement_id"]: r for r in plan.get("matrix_snapshot", [])},
        "new": {r["requirement_id"]: r for r in state["requirements"]},
    })


@router.post("/plans/{plan_id}/update")
def selective_update(request: Request, plan_id: str):
    user, session = require(request, EDITORS | REVIEWERS)
    api_csrf(request, session)
    plan = _plan_access(request, plan_id)
    db = request.app.state.db
    employee = db.employees.find_one({"_id": plan["employee_id"]})
    if employee.get("active_plan_id") != plan_id or not plan.get("published_at"):
        raise HTTPException(409, "Choose the currently assigned published plan.")
    state = matrix_state(db, employee["role_id"])
    if state["unresolved"]:
        raise HTTPException(409, "Resolve rule conflicts before selectively updating.")
    if not state["requirements"]:
        raise HTTPException(409, "No approved requirements remain.")
    job = enqueue(db, user["_id"], "selective", plan["employee_id"], base_plan_id=plan_id)
    return ok({"job_id": job["_id"]}, 201)


# ── Compare ──────────────────────────────────────────────────────────────────

@router.get("/plans/{plan_id}/compare")
def compare(request: Request, plan_id: str):
    plan = _plan_access(request, plan_id)
    db = request.app.state.db
    user, _ = require(request)
    alternatives = list(
        db.plans.find({"employee_id": plan["employee_id"], "_id": {"$ne": plan_id}})
        .sort("created_at", -1).limit(100)
    )
    other_id = request.query_params.get("other", alternatives[0]["_id"] if alternatives else "")
    other = _plan_access(request, other_id) if other_id else None
    if other and other["employee_id"] != plan["employee_id"]:
        raise HTTPException(422, "Compare versions for the same employee.")
    if user["role"] == "employee":
        plan["content"] = public_content(plan["content"])
        if other:
            other["content"] = public_content(other["content"])
    return ok({
        "left": plan,
        "right": other,
        "alternatives": alternatives,
        "comparison": compare_plans(plan, other) if other else None,
    })


# ── Consistency experiments ──────────────────────────────────────────────────

@router.post("/plans/{plan_id}/consistency")
def start_experiment(request: Request, plan_id: str):
    user, session = require(request, EDITORS | REVIEWERS)
    api_csrf(request, session)
    plan = _plan_access(request, plan_id)
    db = request.app.state.db
    employee = db.employees.find_one({"_id": plan["employee_id"]})
    state = matrix_state(db, employee["role_id"])
    if not state["requirements"] or state["unresolved"]:
        raise HTTPException(409, "Approve a non-conflicting role matrix first.")
    key = uid()
    digest = fingerprint(state["requirements"])
    context = {k: employee[k] for k in ("role_id", "department", "experience", "joining_date")}
    jobs = [
        enqueue(
            db, user["_id"], "generate", employee["_id"],
            experiment_id=key, expected_snapshot=digest,
            expected_context=context,
            expected_model=request.app.state.settings.genai_model,
        )["_id"]
        for _ in range(2)
    ]
    db.consistency_experiments.insert_one({
        "_id": key,
        "employee_id": employee["_id"],
        "actor_id": user["_id"],
        "snapshot_digest": digest,
        "employee_snapshot": context,
        "job_ids": jobs,
        "created_at": now(),
    })
    audit(db, user["_id"], "consistency.start", key, {"job_ids": jobs})
    return ok({"experiment_id": key}, 201)


@router.get("/experiments/{experiment_id}")
def experiment_detail(request: Request, experiment_id: str):
    require(request, EDITORS | REVIEWERS)
    db = request.app.state.db
    record = db.consistency_experiments.find_one({"_id": experiment_id})
    if not record:
        raise HTTPException(404, "Experiment not found.")
    _employee_access(request, record["employee_id"])
    jobs = [db.jobs.find_one({"_id": key}) for key in record["job_ids"]]
    plans = [db.plans.find_one({"_id": j.get("result_id")}) for j in jobs]
    comparison = (
        compare_plans(*plans)
        if all(plans) and all(j["status"] == "completed" for j in jobs)
        else None
    )
    if comparison:
        db.consistency_experiments.update_one(
            {"_id": experiment_id},
            {"$set": {"result": {k: v for k, v in comparison.items() if k != "rows"}}},
        )
    return ok({
        "experiment": record,
        "jobs": jobs,
        "plans": plans,
        "comparison": comparison,
    })


# ── Reports ──────────────────────────────────────────────────────────────────

@router.get("/reports")
def reports(request: Request):
    user, _ = require(request)
    db = request.app.state.db
    employees = {e["_id"]: e for e in _employees_for(db, user)}
    q = request.query_params.get("q", "").strip().casefold()[:100]
    role = request.query_params.get("role_id", "")
    status = request.query_params.get("status", "")
    rows = []
    role_states = {}
    for plan in db.plans.find({"employee_id": {"$in": list(employees)}}).sort("created_at", -1):
        employee = employees[plan["employee_id"]]
        if role and employee["role_id"] != role:
            continue
        if q and q not in (employee["name"] + " " + plan["content"]["title"]).casefold():
            continue
        if status and plan["status"] != status:
            continue
        if employee["role_id"] not in role_states:
            role_states[employee["role_id"]] = matrix_state(db, employee["role_id"])
        report = progress_report(db, plan, employee)
        rows.append({
            "plan": plan,
            "employee": employee,
            "progress": report,
            "current": _current(db, plan, employee, role_states[employee["role_id"]]),
            "assigned": employee.get("active_plan_id") == plan["_id"],
        })
    return ok({
        "rows": rows,
        "roles": list(db.job_roles.find()),
        "q": request.query_params.get("q", ""),
        "role_id": role,
        "selected_status": status,
    })
