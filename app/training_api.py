"""Training, learning, and assessment JSON API endpoints for the React SPA."""

from copy import deepcopy
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from .db import uid, now, audit
from .security import require, EDITORS, REVIEWERS
from .schemas import FullOnboardingPlan, FullLearningItem
from .learning import learning_checks, progress_report, public_content, PASS_PERCENT
from .validation import validate_plan
from .worker import matrix, fingerprint, enqueue
from .updates import carry_progress, serialized_learning
from .policy import matrix_state
from .api import _ser, ok, api_csrf, _text, _employee_access, _plan_access, _employees_for

router = APIRouter(prefix="/api")


def _current(db, plan, employee, role_state=None):
    role_state = role_state if role_state is not None else matrix_state(db, employee["role_id"])
    return (
        plan["status"] != "Stale sources"
        and plan["role_id"] == employee["role_id"]
        and all(employee.get(k) == v for k, v in plan.get("employee_snapshot", {}).items())
        and not role_state["unresolved"]
        and plan.get("snapshot_digest") == fingerprint(role_state["requirements"])
    )


def _inspect_plan(db, content, employee):
    try:
        parsed = FullOnboardingPlan.model_validate(content)
    except ValidationError:
        raise HTTPException(
            422,
            "The plan needs complete Phase 2 lessons and assessments.",
        ) from None
    requirements = matrix(db, employee["role_id"])
    ids = list({r["document_id"] for r in requirements})
    validation = validate_plan(
        parsed, requirements,
        list(db.documents.find({"_id": {"$in": ids}})),
        list(db.source_sections.find({"document_id": {"$in": ids}})),
        employee["role_id"],
    )
    return validation, learning_checks(content), requirements


def _context(request, plan_id, active=False):
    plan = _plan_access(request, plan_id)
    user, session, employee = _employee_access(request, plan["employee_id"])
    db = request.app.state.db
    fresh = _current(db, plan, employee)
    if active and (
        plan["status"] != "Published"
        or employee.get("active_plan_id") != plan_id
        or not fresh
    ):
        raise HTTPException(409, "This is not the current published plan, or its sources changed.")
    return db, plan, employee, user, session, fresh


def _learner_item(request, plan_id, requirement_id):
    db, plan, employee, user, session, _ = _context(request, plan_id, active=True)
    api_csrf(request, session)
    if user["role"] != "employee" or employee.get("user_id") != user["_id"]:
        raise HTTPException(403, "Only the assigned employee can submit learning work.")
    report = progress_report(db, plan, employee)
    row = next(
        (r for r in report["rows"] if r["item"]["requirement_id"] == requirement_id), None
    )
    if not row:
        raise HTTPException(404, "Learning item not found.")
    if row["blocked_by"]:
        raise HTTPException(409, "Complete prerequisite modules first: " + ", ".join(row["blocked_by"]))
    return db, plan, employee, user, row


# ── Learning home ─────────────────────────────────────────────────────────────

@router.get("/learning")
def learning_home(request: Request):
    user, _ = require(request)
    db = request.app.state.db
    cards = []
    for employee in _employees_for(db, user):
        plan = db.plans.find_one({"_id": employee.get("active_plan_id", "")})
        cards.append({
            "employee": employee,
            "plan": plan,
            "fresh": _current(db, plan, employee) if plan else False,
            "report": progress_report(db, plan, employee) if plan else None,
        })
    return ok({"cards": cards})


@router.get("/learning/{plan_id}")
def learn_workspace(request: Request, plan_id: str):
    db, plan, employee, user, _, fresh = _context(request, plan_id)
    report = progress_report(db, plan, employee)
    active = (
        plan["status"] == "Published"
        and employee.get("active_plan_id") == plan_id
        and fresh
    )
    if user["role"] == "employee":
        for row in report["rows"]:
            row["item"] = public_content({"items": [row["item"]]})["items"][0]
    return ok({
        "plan": plan,
        "employee": employee,
        "report": report,
        "active": active,
        "is_learner": user["role"] == "employee",
        "pass_percent": PASS_PERCENT,
    })


# ── Plan review ───────────────────────────────────────────────────────────────

class ReviewBody(BaseModel):
    decision: str
    comment: str
    confirmed: str = ""


@router.post("/plans/{plan_id}/review")
@serialized_learning
def review_plan(request: Request, plan_id: str, body: ReviewBody):
    user, session = require(request, REVIEWERS)
    api_csrf(request, session)
    db, plan, employee, _, _, fresh = _context(request, plan_id)
    if body.decision not in ["approve", "reject", "comment"]:
        raise HTTPException(422, "Choose a valid review action.")
    comment = _text(body.comment, "Review comment", 3000)
    if body.decision != "comment":
        if plan["status"] == "Published":
            raise HTTPException(409, "Published content is immutable.")
        if body.decision == "approve":
            if body.confirmed != "true":
                raise HTTPException(422, "Confirm that you reviewed all content.")
            validation, teaching, requirements = _inspect_plan(db, plan["content"], employee)
            if not fresh or not validation["core_passed"] or not teaching["passed"]:
                raise HTTPException(409, "Resolve validation findings and stale sources before publishing.")
            updates = {
                "status": "Published",
                "published_by": user["_id"],
                "published_at": now(),
                "publication_validation": validation,
                "learning_checks": teaching,
            }
            carry_progress(db, plan, employee)
        else:
            updates = {"status": "Rejected"}
        result = db.plans.update_one(
            {"_id": plan_id, "status": plan["status"]}, {"$set": updates}
        )
        if not result.matched_count:
            raise HTTPException(409, "Another reviewer changed this plan. Refresh before deciding.")
        if body.decision == "approve":
            db.employees.update_one(
                {"_id": employee["_id"]}, {"$set": {"active_plan_id": plan_id}}
            )
    db.plan_reviews.insert_one({
        "_id": uid(),
        "plan_id": plan_id,
        "actor_id": user["_id"],
        "actor_name": user["name"],
        "decision": body.decision,
        "comment": comment,
        "created_at": now(),
    })
    audit(db, user["_id"], "plan." + body.decision, plan_id, {"comment": comment})
    return JSONResponse(None, status_code=204)


@router.post("/plans/{plan_id}/regenerate")
def regenerate_plan(request: Request, plan_id: str):
    user, session = require(request, EDITORS | REVIEWERS)
    api_csrf(request, session)
    plan = _plan_access(request, plan_id)
    job = enqueue(request.app.state.db, user["_id"], "generate", plan["employee_id"])
    return ok({"job_id": job["_id"]}, 201)


# ── Plan edit ─────────────────────────────────────────────────────────────────

@router.get("/plans/{plan_id}/items/{requirement_id}/edit")
def edit_item_get(request: Request, plan_id: str, requirement_id: str):
    require(request, EDITORS | REVIEWERS)
    plan = _plan_access(request, plan_id)
    item = next(
        (i for i in plan["content"]["items"] if i["requirement_id"] == requirement_id), None
    )
    if not item:
        raise HTTPException(404, "Learning item not found.")
    if "quiz" not in item:
        raise HTTPException(409, "Regenerate this legacy plan to add Phase 2 content first.")
    return ok({"plan": plan, "item": item})


@router.post("/plans/{plan_id}/items/{requirement_id}/edit")
async def edit_item_post(request: Request, plan_id: str, requirement_id: str):
    user, session = require(request, EDITORS | REVIEWERS)
    body = await request.json()
    api_csrf(request, session)
    db, plan, employee, _, _, fresh = _context(request, plan_id)
    if not fresh:
        raise HTTPException(409, "Sources changed. Regenerate before editing.")
    content = deepcopy(plan["content"])
    item = next((i for i in content["items"] if i["requirement_id"] == requirement_id), None)
    if not item or "quiz" not in item:
        raise HTTPException(404, "Phase 2 learning item not found.")
    for field in ["module_title", "learning_objective", "lesson", "practical_activity", "stage"]:
        item[field] = _text(body.get(field, ""), field.replace("_", " "))
    try:
        item["estimated_minutes"] = int(body.get("estimated_minutes", 0))
        item["checklist"] = [x.strip() for x in body.get("checklist", []) if x.strip()]
        item["scenario"] = {
            "prompt": _text(body.get("scenario_prompt", ""), "Scenario"),
            "expected_response": _text(body.get("scenario_expected", ""), "Expected scenario response"),
        }
        item["quiz"] = {
            "question": _text(body.get("question", ""), "Quiz question"),
            "options": [x.strip() for x in body.get("options", []) if x.strip()],
            "correct_index": int(body.get("correct_index", 0)),
            "explanation": _text(body.get("explanation", ""), "Answer explanation"),
            "evidence_quote": item["source_quote"],
        }
        item["rubric"] = [
            {
                "criterion": _text(r.get("criterion", ""), "Rubric criterion"),
                "max_points": int(r.get("max_points", 1)),
            }
            for r in body.get("rubric", [])
        ]
        FullLearningItem.model_validate(item)
    except (ValueError, ValidationError):
        raise HTTPException(422, "Check quiz, checklist, stage, minutes and rubric.") from None
    reason = _text(body.get("reason", ""), "Edit reason", 3000)
    validation, teaching, requirements = _inspect_plan(db, content, employee)
    key = uid()
    new = {
        k: deepcopy(plan[k])
        for k in ("employee_id", "role_id", "source_document_ids", "model", "prompt_version", "generation")
    }
    new.update({
        "_id": key,
        "parent_plan_id": plan_id,
        "root_plan_id": plan.get("root_plan_id", plan_id),
        "carry_parent_plan_id": plan.get("carry_parent_plan_id"),
        "employee_snapshot": plan.get("employee_snapshot", {}),
        "content": content,
        "status": validation["status"],
        "validation": validation,
        "learning_checks": teaching,
        "matrix_snapshot": requirements,
        "snapshot_digest": fingerprint(requirements),
        "created_by": user["_id"],
        "created_at": now(),
        "origin": "human_edit",
    })
    db.plans.insert_one(new)
    db.plan_reviews.insert_one({
        "_id": uid(),
        "plan_id": key,
        "actor_id": user["_id"],
        "actor_name": user["name"],
        "decision": "edit",
        "comment": reason,
        "created_at": now(),
    })
    audit(db, user["_id"], "plan.edit", key,
          {"parent_plan_id": plan_id, "requirement_id": requirement_id, "reason": reason})
    return ok({"plan_id": key}, 201)


# ── Learner progress ─────────────────────────────────────────────────────────

class ProgressBody(BaseModel):
    lesson_read: bool = False
    checked: list[int] = []


@router.post("/learning/{plan_id}/{requirement_id}/progress")
@serialized_learning
def save_progress(request: Request, plan_id: str, requirement_id: str, body: ProgressBody):
    db, plan, employee, user, row = _learner_item(request, plan_id, requirement_id)
    checked = sorted(set(body.checked))
    if any(i < 0 or i >= len(row["item"]["checklist"]) for i in checked):
        raise HTTPException(422, "Checklist entry does not exist.")
    key = {"plan_id": plan_id, "employee_id": employee["_id"], "requirement_id": requirement_id}
    db.learning_progress.update_one(
        key,
        {
            "$set": {"checked": checked, "lesson_read": body.lesson_read, "updated_at": now()},
            "$setOnInsert": {"_id": uid(), **key},
        },
        upsert=True,
    )
    audit(db, user["_id"], "learning.progress", plan_id, {"requirement_id": requirement_id})
    return JSONResponse(None, status_code=204)


class QuizBody(BaseModel):
    answer: int


@router.post("/learning/{plan_id}/{requirement_id}/quiz")
@serialized_learning
def submit_quiz(request: Request, plan_id: str, requirement_id: str, body: QuizBody):
    db, plan, employee, user, row = _learner_item(request, plan_id, requirement_id)
    question = row["item"]["quiz"]
    if not 0 <= body.answer < len(question["options"]):
        raise HTTPException(422, "Select an existing answer.")
    passed = body.answer == question["correct_index"]
    db.quiz_attempts.insert_one({
        "_id": uid(),
        "plan_id": plan_id,
        "employee_id": employee["_id"],
        "requirement_id": requirement_id,
        "answer": body.answer,
        "score": 100 if passed else 0,
        "passed": passed,
        "feedback": question["explanation"],
        "created_at": now(),
    })
    audit(db, user["_id"], "learning.quiz", plan_id,
          {"requirement_id": requirement_id, "score": 100 if passed else 0})
    return ok({"score": 100 if passed else 0, "passed": passed, "feedback": question["explanation"]})


class PracticalBody(BaseModel):
    scenario_response: str
    practical_response: str


@router.post("/learning/{plan_id}/{requirement_id}/submit")
@serialized_learning
def submit_practical(request: Request, plan_id: str, requirement_id: str, body: PracticalBody):
    db, plan, employee, user, row = _learner_item(request, plan_id, requirement_id)
    if row["practical_passed"] or (
        row["latest_submission"] and row["latest_submission"]["status"] == "pending"
    ):
        raise HTTPException(409, "This activity already passed or has a submission awaiting assessment.")
    key = uid()
    db.practical_submissions.insert_one({
        "_id": key,
        "plan_id": plan_id,
        "employee_id": employee["_id"],
        "requirement_id": requirement_id,
        "status": "pending",
        "scenario_response": _text(body.scenario_response, "Scenario response"),
        "practical_response": _text(body.practical_response, "Practical response"),
        "created_at": now(),
    })
    audit(db, user["_id"], "learning.submit", key)
    return JSONResponse(None, status_code=204)


# ── Assessments ───────────────────────────────────────────────────────────────

@router.get("/assessments")
def assessment_queue(request: Request):
    user, _ = require(request, REVIEWERS | {"manager"})
    db = request.app.state.db
    employees = {e["_id"]: e for e in _employees_for(db, user)}
    submissions = list(
        db.practical_submissions.find({
            "employee_id": {"$in": list(employees)},
            "plan_id": {"$in": [e.get("active_plan_id", "") for e in employees.values()]},
            "status": "pending",
        }).sort("created_at", 1)
    )
    return ok({"submissions": submissions, "employees": employees})


@router.post("/submissions/{submission_id}/grade")
@serialized_learning
async def grade_submission(request: Request, submission_id: str):
    user, session = require(request, REVIEWERS | {"manager"})
    body = await request.json()
    api_csrf(request, session)
    db = request.app.state.db
    submission = db.practical_submissions.find_one({"_id": submission_id})
    if not submission:
        raise HTTPException(404, "Submission not found.")
    db2, plan, employee, _, _, _ = _context(request, submission["plan_id"], active=True)
    item = next(
        i for i in plan["content"]["items"]
        if i["requirement_id"] == submission["requirement_id"]
    )
    try:
        scores = [int(body.get(f"score_{i}", 0)) for i in range(len(item["rubric"]))]
    except (ValueError, TypeError):
        raise HTTPException(422, "Provide whole-number scores for every rubric criterion.") from None
    if any(s < 0 or s > r["max_points"] for s, r in zip(scores, item["rubric"])):
        raise HTTPException(422, "Scores must be within the rubric limits.")
    maximum = sum(r["max_points"] for r in item["rubric"])
    percent = round(100 * sum(scores) / maximum, 1)
    feedback = _text(body.get("feedback", ""), "Assessor feedback", 3000)
    result = db.practical_submissions.update_one(
        {"_id": submission_id, "status": "pending"},
        {"$set": {
            "status": "graded",
            "scores": scores,
            "maximum": maximum,
            "percent": percent,
            "passed": 100 * sum(scores) >= PASS_PERCENT * maximum,
            "feedback": feedback,
            "graded_by": user["_id"],
            "graded_at": now(),
        }},
    )
    if not result.matched_count:
        raise HTTPException(409, "This submission was already graded.")
    audit(db, user["_id"], "learning.grade", submission_id,
          {"scores": scores, "percent": percent, "feedback": feedback})
    return JSONResponse(None, status_code=204)
