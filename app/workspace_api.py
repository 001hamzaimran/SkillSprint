"""Workspace administration, review queue, search, and progress evaluation."""

from copy import deepcopy
from datetime import date, timedelta
import secrets

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .api import (
    ok,
    api_csrf,
    _employees_for,
    _employee_access,
    _plan_access,
    _nonempty,
    _job_access,
)
from .db import now, uid, audit
from .learning import STAGE_DAYS, progress_report
from .schemas import STAGES
from .security import require, REVIEWERS, EDITORS, hash_password, token_hash
from .mail import send_password_reset
from .policy import matrix_state
from .comparison import compare_plans
from .worker import enqueue

router = APIRouter(prefix="/api")


@router.post("/jobs/{job_id}/retry")
def retry_job(request: Request, job_id: str):
    user, session = require(request, EDITORS | REVIEWERS)
    api_csrf(request, session)
    original = _job_access(request, job_id)
    if original["status"] != "failed":
        raise HTTPException(409, "Only failed jobs can be retried.")
    if original.get("experiment_id"):
        raise HTTPException(409, "Start a new controlled experiment to retry both runs.")
    context = {"retry_of": job_id}
    if original.get("base_plan_id"):
        context["base_plan_id"] = original["base_plan_id"]
    job = enqueue(
        request.app.state.db, user["_id"], original["kind"], original["target_id"], **context
    )
    return ok({"job_id": job["_id"]}, 201)


@router.get("/requirements/{requirement_id}")
def requirement_details(request: Request, requirement_id: str):
    require(request, REVIEWERS)
    db = request.app.state.db
    record = db.requirements.find_one({"_id": requirement_id})
    if not record:
        raise HTTPException(404, "Requirement not found.")
    available = list(db.requirements.find({"status": "approved"}))
    suggestions = [
        r
        for r in available
        if r["document_id"] == record["document_id"]
        and r["section_id"] in record.get("suggested_prerequisite_sections", [])
        and r["_id"] != record["_id"]
    ]
    return ok({"requirement": record, "available": available, "suggestions": suggestions})


def stage_settings(db):
    return (db.workspace_settings.find_one({"_id": "stages"}) or {}).get("days", STAGE_DAYS)


class StageBody(BaseModel):
    days: dict[str, int]


@router.get("/settings/stages")
def get_stages(request: Request):
    require(request)
    return ok({"days": stage_settings(request.app.state.db)})


@router.put("/settings/stages")
def set_stages(request: Request, body: StageBody):
    user, session = require(request, {"admin"})
    api_csrf(request, session)
    if set(body.days) != set(STAGES):
        raise HTTPException(422, "Provide all six onboarding stages.")
    days = [body.days[stage] for stage in STAGES]
    if days[0] != 0 or any(day < 0 or day > 365 for day in days) or days != sorted(set(days)):
        raise HTTPException(422, "Start Day 1 at zero and use increasing day offsets up to 365.")
    db = request.app.state.db
    before = stage_settings(db)
    db.workspace_settings.replace_one(
        {"_id": "stages"}, {"_id": "stages", "days": body.days}, upsert=True
    )
    audit(db, user["_id"], "settings.stages", "stages", {"before": before, "after": body.days})
    return ok({"days": body.days})


class EmployeeUpdate(BaseModel):
    name: str
    role_id: str
    joining_date: str
    experience: str
    manager_id: str = ""
    user_id: str = ""


@router.put("/employees/{employee_id}")
def update_employee(request: Request, employee_id: str, body: EmployeeUpdate):
    user, session = require(request, EDITORS)
    api_csrf(request, session)
    _, _, before = _employee_access(request, employee_id)
    db = request.app.state.db
    role = db.job_roles.find_one({"_id": body.role_id})
    if not role or body.experience not in ["Beginner", "Intermediate", "Advanced"]:
        raise HTTPException(422, "Choose a valid role and experience level.")
    try:
        date.fromisoformat(body.joining_date)
    except ValueError:
        raise HTTPException(422, "Use a valid joining date.") from None
    for account, roles in ((body.manager_id, ["admin", "manager"]), (body.user_id, ["employee"])):
        if account and not db.users.find_one(
            {"_id": account, "role": {"$in": roles}, "active": True}
        ):
            raise HTTPException(422, "Choose an active account with the appropriate role.")
    changes = body.model_dump()
    changes.update(
        name=_nonempty(body.name, "Name"), role_name=role["name"], department=role["department"]
    )
    db.employees.update_one({"_id": employee_id}, {"$set": changes})
    if any(
        before.get(key) != changes[key]
        for key in ("role_id", "department", "experience", "joining_date")
    ):
        db.plans.update_many({"employee_id": employee_id}, {"$set": {"status": "Stale sources"}})
    audit(db, user["_id"], "employee.update", employee_id, {"before": before, "after": changes})
    return ok({"employee": db.employees.find_one({"_id": employee_id})})


class RoleUpdate(BaseModel):
    name: str
    department: str
    description: str = ""


@router.put("/roles/{role_id}")
def update_role(request: Request, role_id: str, body: RoleUpdate):
    user, session = require(request, EDITORS)
    api_csrf(request, session)
    db = request.app.state.db
    before = db.job_roles.find_one({"_id": role_id})
    if not before:
        raise HTTPException(404, "Role not found.")
    changes = {
        "name": _nonempty(body.name, "Role name"),
        "department": _nonempty(body.department, "Department"),
        "description": body.description[:2000],
    }
    db.job_roles.update_one({"_id": role_id}, {"$set": changes})
    db.employees.update_many(
        {"role_id": role_id},
        {"$set": {"role_name": changes["name"], "department": changes["department"]}},
    )
    if before["department"] != changes["department"]:
        db.plans.update_many({"role_id": role_id}, {"$set": {"status": "Stale sources"}})
    audit(db, user["_id"], "role.update", role_id, {"before": before, "after": changes})
    return ok({"role": db.job_roles.find_one({"_id": role_id})})


@router.get("/review-queue")
def review_queue(request: Request):
    user, _ = require(request, REVIEWERS)
    db = request.app.state.db
    plans = list(
        db.plans.find(
            {"status": {"$in": ["Review required", "Needs correction", "Stale sources"]}}
        ).sort("created_at", -1)
    )
    return ok({"plans": plans, "employees": {e["_id"]: e for e in _employees_for(db, user)}})


class OverrideBody(BaseModel):
    code: str
    requirement_id: str = ""
    reason: str = Field(min_length=10, max_length=3000)


@router.post("/plans/{plan_id}/overrides")
def override_recommendation(request: Request, plan_id: str, body: OverrideBody):
    user, session = require(request, REVIEWERS)
    api_csrf(request, session)
    plan = _plan_access(request, plan_id)
    # The SRS permits recommendation overrides; source coverage and access rules remain mandatory.
    warning = next(
        (
            w
            for w in plan["validation"].get("warnings", [])
            if w["code"] == body.code and w.get("requirement_id", "") == body.requirement_id
        ),
        None,
    )
    if not warning:
        raise HTTPException(
            422, "Choose an existing advisory warning. Core validation failures require correction."
        )
    record = {
        "_id": uid(),
        "plan_id": plan_id,
        "actor_id": user["_id"],
        "actor_name": user["name"],
        "decision": "override",
        "comment": body.reason.strip(),
        "original_result": deepcopy(warning),
        "created_at": now(),
    }
    db = request.app.state.db
    db.plan_reviews.insert_one(record)
    audit(db, user["_id"], "plan.override", plan_id, record)
    return ok({"decision": record}, 201)


@router.get("/search")
def search(request: Request):
    user, _ = require(request)
    db = request.app.state.db
    query = request.query_params.get("q", "").strip().casefold()[:100]
    department = request.query_params.get("department", "").casefold()
    status = request.query_params.get("status", "")
    employees = [
        e
        for e in _employees_for(db, user)
        if not department or department in e["department"].casefold()
    ]

    def match(*values):
        return not query or query in " ".join(str(value) for value in values).casefold()

    plans = list(db.plans.find({"employee_id": {"$in": [e["_id"] for e in employees]}}))
    return ok(
        {
            "employees": [
                e for e in employees if match(e["name"], e["role_name"], e["department"])
            ],
            "roles": (
                [r for r in db.job_roles.find() if match(r["name"], r["department"])]
                if user["role"] in EDITORS | REVIEWERS
                else []
            ),
            "documents": (
                [
                    d
                    for d in db.documents.find()
                    if match(d["title"], d["document_id"]) and (not status or d["status"] == status)
                ]
                if user["role"] in EDITORS | REVIEWERS
                else []
            ),
            "modules": [
                {
                    "plan_id": p["_id"],
                    "employee_id": p["employee_id"],
                    "status": p["status"],
                    "item": i,
                }
                for p in plans
                if not status or p["status"] == status
                for i in p["content"]["items"]
                if match(i["module_title"], i["lesson"], i["requirement_id"])
            ],
        }
    )


def evaluate_progress(db):
    """Persist hourly assessments for assigned employees; recommendations use actual work."""
    for employee in db.employees.find({"active_plan_id": {"$exists": True}}):
        plan = db.plans.find_one({"_id": employee.get("active_plan_id")})
        if not plan:
            continue
        report = progress_report(db, plan, employee)
        db.progress_evaluations.replace_one(
            {"_id": employee["_id"]},
            {
                "_id": employee["_id"],
                "plan_id": plan["_id"],
                "status": report["status"],
                "percent": report["percent"],
                "evaluated_at": now(),
                "recommendations": [
                    {
                        "requirement_id": row["item"]["requirement_id"],
                        "competency": row["competency"],
                        "recommendation": row["suggestion"],
                    }
                    for row in report["weak"]
                ],
            },
            upsert=True,
        )


@router.get("/insights")
def insights(request: Request):
    user, _ = require(request)
    db = request.app.state.db
    people = []
    roles = {}
    for employee in _employees_for(db, user):
        plan = db.plans.find_one({"_id": employee.get("active_plan_id", "")})
        report = progress_report(db, plan, employee) if plan else None
        people.append(
            {
                "employee": employee,
                "plan_id": plan["_id"] if plan else None,
                "status": report["status"] if report else "Not assigned",
                "percent": report["percent"] if report else 0,
                "recommendations": (
                    [
                        {"competency": r["competency"], "message": r["suggestion"]}
                        for r in report["weak"]
                    ]
                    if report
                    else []
                ),
            }
        )
        row = roles.setdefault(
            employee["role_id"],
            {"name": employee["role_name"], "employees": 0, "completed": 0, "progress_total": 0},
        )
        row["employees"] += 1
        row["completed"] += bool(report and report["status"] == "Completed")
        row["progress_total"] += report["percent"] if report else 0
    return ok(
        {
            "people": people,
            "roles": [
                {
                    "role_id": key,
                    **row,
                    "average_progress": round(row["progress_total"] / row["employees"]),
                }
                for key, row in roles.items()
            ],
        }
    )


@router.get("/compare")
def compare_across_profiles(request: Request, left: str, right: str):
    require(request, EDITORS | REVIEWERS)
    a, b = _plan_access(request, left), _plan_access(request, right)
    return ok({"left": a, "right": b, "comparison": compare_plans(a, b)})


class EmailBody(BaseModel):
    email: str = Field(max_length=254)


@router.post("/auth/forgot-password")
def forgot_password(request: Request, body: EmailBody):
    db, settings = request.app.state.db, request.app.state.settings
    email = body.email.strip().lower()
    ip = request.client.host if request.client else "unknown"
    key = token_hash("reset-api|" + ip)
    limit = db.login_limits.find_one({"_id": key, "expires_at": {"$gt": now()}})
    if not limit:
        db.login_limits.replace_one(
            {"_id": key},
            {"_id": key, "count": 0, "expires_at": now() + timedelta(minutes=15)},
            upsert=True,
        )
    db.login_limits.update_one({"_id": key}, {"$inc": {"count": 1}})
    result = {"message": "If this active account exists, a password reset email will be sent."}
    user = (
        db.users.find_one({"email": email, "active": True})
        if not limit or limit["count"] < 5
        else None
    )
    if user:
        raw = secrets.token_urlsafe(48)
        db.password_resets.delete_many({"user_id": user["_id"]})
        db.password_resets.insert_one(
            {
                "_id": uid(),
                "user_id": user["_id"],
                "token_hash": token_hash(raw),
                "expires_at": now() + timedelta(minutes=30),
            }
        )
        url = settings.frontend_url.rstrip("/") + "/reset-password?token=" + raw
        try:
            delivered = send_password_reset(settings, email, url)
        except Exception:
            delivered = False
        audit(
            db, user["_id"], "password.reset_requested", user["_id"], {"email_delivered": delivered}
        )
        if settings.app_env == "development":
            result["development_reset_url"] = url
    return ok(result)


class ResetBody(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=12, max_length=128)


@router.post("/auth/reset-password")
def reset_password(request: Request, body: ResetBody):
    db = request.app.state.db
    encoded = hash_password(body.password)
    record = db.password_resets.find_one_and_delete(
        {"token_hash": token_hash(body.token), "expires_at": {"$gt": now()}}
    )
    if not record:
        raise HTTPException(422, "This reset link is invalid or expired.")
    db.users.update_one(
        {"_id": record["user_id"], "active": True}, {"$set": {"password_hash": encoded}}
    )
    db.sessions.delete_many({"user_id": record["user_id"]})
    db.password_resets.delete_many({"user_id": record["user_id"]})
    audit(db, record["user_id"], "password.reset_completed", record["user_id"])
    return ok({"message": "Password updated. Sign in with your new password."})
