"""JSON API endpoints for the React SPA frontend."""

import re
from datetime import date, datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from .db import now, uid, audit
from .security import (
    require,
    identity,
    csrf as csrf_check,
    new_session,
    verify_password,
    hash_password,
    can_read_employee,
    token_hash,
    ROLES,
    EDITORS,
    REVIEWERS,
)
from .ingestion import ingest, normalized, SUSPICIOUS
from .schemas import STAGES
from .worker import enqueue, matrix
from .learning import public_content, learning_checks

router = APIRouter(prefix="/api")


# ── Serialisation ──────────────────────────────────────────────────────────────


def _ser(obj):
    """Recursively convert stored PostgreSQL JSONB documents to JSON-safe dictionaries."""
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _ser(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_ser(v) for v in obj]
    return obj


def ok(data, status_code=200):
    return JSONResponse(_ser(data), status_code=status_code)


# ── CSRF helper for JSON requests ─────────────────────────────────────────────


def api_csrf(request, session):
    """Validate CSRF token from X-CSRF-Token header."""
    token = request.headers.get("X-CSRF-Token", "")
    csrf_check(request, session, token)


# ── Shared access helpers ─────────────────────────────────────────────────────


def _nonempty(value, label, limit=180):
    value = value.strip()
    if not value or len(value) > limit:
        raise HTTPException(422, f"{label} is required and must be at most {limit} characters.")
    return value


def _text(value, label, limit=5000):
    value = str(value).strip()
    if not value or len(value) > limit:
        raise HTTPException(422, f"{label} is required and must be at most {limit} characters.")
    return value


def _employees_for(db, user):
    query = {}
    if user["role"] == "employee":
        query = {"user_id": user["_id"]}
    if user["role"] == "manager":
        query = {"manager_id": user["_id"]}
    return list(db.employees.find(query).sort("name", 1).limit(1000))


def _employee_access(request, employee_id):
    user, session = require(request)
    employee = request.app.state.db.employees.find_one({"_id": employee_id})
    if not employee or not can_read_employee(user, employee):
        raise HTTPException(404, "Employee not found.")
    return user, session, employee


def _plan_access(request, plan_id):
    plan = request.app.state.db.plans.find_one({"_id": plan_id})
    if not plan:
        raise HTTPException(404, "Plan not found.")
    _employee_access(request, plan["employee_id"])
    return plan


def _job_access(request, job_id):
    user, _ = require(request)
    job = request.app.state.db.jobs.find_one({"_id": job_id})
    if not job or (job["actor_id"] != user["_id"] and user["role"] != "admin"):
        raise HTTPException(404, "Job not found.")
    return job


# ── Auth endpoints ─────────────────────────────────────────────────────────────


class LoginBody(BaseModel):
    email: str
    password: str


@router.get("/auth/me")
def auth_me(request: Request):
    user, session = identity(request)
    if not user:
        raise HTTPException(401, "Not authenticated.")
    safe_user = {key: value for key, value in user.items() if key != "password_hash"}
    return ok({"user": safe_user, "csrf_token": session["csrf"]})


@router.post("/auth/login")
def auth_login(request: Request, body: LoginBody):
    db = request.app.state.db
    settings = request.app.state.settings
    email = body.email.strip().lower()[:254]
    ip = request.client.host if request.client else "unknown"
    key = token_hash(ip + "|" + email)
    window = db.login_limits.find_one({"_id": key, "expires_at": {"$gt": now()}})
    if window and window["count"] >= 8:
        raise HTTPException(429, "Too many sign-in attempts. Try again in 15 minutes.")
    from datetime import timedelta

    if not window:
        db.login_limits.replace_one(
            {"_id": key},
            {"_id": key, "count": 0, "expires_at": now() + timedelta(minutes=15)},
            upsert=True,
        )
    db.login_limits.update_one({"_id": key}, {"$inc": {"count": 1}})
    user = db.users.find_one({"email": email, "active": True})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Email or password is incorrect.")
    db.login_limits.delete_one({"_id": key})
    token = new_session(db, user["_id"])
    # Get the new session to return CSRF token
    session = db.sessions.find_one({"token_hash": token_hash(token)})
    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    response = ok({"user": safe_user, "csrf_token": session["csrf"]})
    response.set_cookie(
        "skillsprint_session",
        token,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
        max_age=8 * 3600,
    )
    audit(db, user["_id"], "auth.login", user["_id"])
    return response


@router.post("/auth/logout")
def auth_logout(request: Request):
    user, session = require(request)
    api_csrf(request, session)
    request.app.state.db.sessions.delete_one({"_id": session["_id"]})
    response = JSONResponse(None, status_code=204)
    response.delete_cookie("skillsprint_session")
    return response


# ── Dashboard ──────────────────────────────────────────────────────────────────


@router.get("/dashboard")
def dashboard(request: Request):
    user, _ = require(request)
    db = request.app.state.db
    settings = request.app.state.settings
    employees = _employees_for(db, user)
    eids = [e["_id"] for e in employees]
    plans = list(
        db.plans.find({"employee_id": {"$in": eids}}, {"matrix_snapshot": 0})
        .sort("created_at", -1)
        .limit(8)
    )
    stats = {
        "employees": len(employees),
        "plans": db.plans.count_documents({"employee_id": {"$in": eids}}),
    }
    if user["role"] in EDITORS | REVIEWERS:
        stats.update(
            documents=db.documents.count_documents({}),
            approved=db.requirements.count_documents({"status": "approved"}),
        )
    return ok({"stats": stats, "plans": plans, "ai_ready": bool(settings.openai_api_key)})


# ── Roles ──────────────────────────────────────────────────────────────────────


@router.get("/roles")
def roles_list(request: Request):
    require(request, EDITORS | REVIEWERS)
    return ok({"roles": list(request.app.state.db.job_roles.find().sort("name", 1))})


class RoleBody(BaseModel):
    name: str
    department: str
    description: str = ""


@router.post("/roles")
def roles_create(request: Request, body: RoleBody):
    user, session = require(request, EDITORS)
    api_csrf(request, session)
    db = request.app.state.db
    role = {
        "_id": uid(),
        "name": _nonempty(body.name, "Role name"),
        "department": _nonempty(body.department, "Department"),
        "description": body.description[:2000],
        "created_at": now(),
    }
    db.job_roles.insert_one(role)
    audit(db, user["_id"], "role.create", role["_id"])
    return ok({"role": role}, 201)


# ── Employees ──────────────────────────────────────────────────────────────────


@router.get("/employees")
def employees_list(request: Request):
    user, _ = require(request)
    db = request.app.state.db
    return ok(
        {
            "employees": _employees_for(db, user),
            "roles": list(db.job_roles.find()),
            "managers": (
                list(db.users.find({"role": {"$in": ["manager", "admin"]}}, {"password_hash": 0}))
                if user["role"] in EDITORS
                else []
            ),
            "accounts": (
                list(db.users.find({"role": "employee"}, {"password_hash": 0}))
                if user["role"] in EDITORS
                else []
            ),
        }
    )


class EmployeeBody(BaseModel):
    name: str
    role_id: str
    joining_date: str
    experience: str = "Beginner"
    manager_id: str = ""
    user_id: str = ""


@router.post("/employees")
def employees_create(request: Request, body: EmployeeBody):
    user, session = require(request, EDITORS)
    api_csrf(request, session)
    db = request.app.state.db
    role = db.job_roles.find_one({"_id": body.role_id})
    if not role:
        raise HTTPException(422, "Choose an existing job role.")
    if body.experience not in ["Beginner", "Intermediate", "Advanced"]:
        raise HTTPException(422, "Invalid experience level.")
    try:
        date.fromisoformat(body.joining_date)
    except ValueError:
        raise HTTPException(422, "Use a valid joining date.")
    if body.manager_id and not db.users.find_one(
        {"_id": body.manager_id, "role": {"$in": ["admin", "manager"]}}
    ):
        raise HTTPException(422, "Invalid manager account.")
    if body.user_id and not db.users.find_one({"_id": body.user_id, "role": "employee"}):
        raise HTTPException(422, "Invalid employee account.")
    record = {
        "_id": uid(),
        "name": _nonempty(body.name, "Employee name"),
        "role_id": body.role_id,
        "role_name": role["name"],
        "department": role["department"],
        "joining_date": body.joining_date,
        "experience": body.experience,
        "manager_id": body.manager_id,
        "user_id": body.user_id,
        "created_at": now(),
    }
    db.employees.insert_one(record)
    audit(db, user["_id"], "employee.create", record["_id"])
    return ok({"employee": record}, 201)


@router.post("/employees/{employee_id}/generate")
def employees_generate(request: Request, employee_id: str):
    user, session = require(request, EDITORS)
    api_csrf(request, session)
    if not request.app.state.db.employees.find_one({"_id": employee_id}):
        raise HTTPException(404, "Employee not found.")
    job = enqueue(request.app.state.db, user["_id"], "generate", employee_id)
    return ok({"job_id": job["_id"]}, 201)


class LinkAccountBody(BaseModel):
    user_id: str = ""


@router.post("/employees/{employee_id}/account")
def employees_link_account(request: Request, employee_id: str, body: LinkAccountBody):
    user, session = require(request, EDITORS)
    api_csrf(request, session)
    _, _, employee = _employee_access(request, employee_id)
    db = request.app.state.db
    if body.user_id and not db.users.find_one(
        {"_id": body.user_id, "role": "employee", "active": True}
    ):
        raise HTTPException(422, "Choose an active employee login.")
    db.employees.update_one({"_id": employee_id}, {"$set": {"user_id": body.user_id}})
    audit(
        db,
        user["_id"],
        "employee.link_account",
        employee_id,
        {"previous": employee.get("user_id", ""), "user_id": body.user_id},
    )
    return JSONResponse(None, status_code=204)


# ── Documents ──────────────────────────────────────────────────────────────────


@router.get("/documents")
def documents_list(request: Request):
    require(request, EDITORS | REVIEWERS)
    db = request.app.state.db
    q = request.query_params.get("q", "").strip()[:100]
    query = {"title": {"$regex": re.escape(q), "$options": "i"}} if q else {}
    return ok(
        {
            "documents": list(db.documents.find(query).sort("created_at", -1).limit(100)),
            "roles": list(db.job_roles.find()),
        }
    )


@router.post("/documents/upload")
async def documents_upload(request: Request):
    user, session = require(request, EDITORS)
    form = await request.form()
    api_csrf(request, session)
    settings = request.app.state.settings
    file = form.get("file")
    if not file:
        raise HTTPException(422, "A file is required.")
    document_id = str(form.get("document_id", ""))
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,60}", document_id):
        raise HTTPException(
            422, "Document ID must use 2-60 letters, numbers, underscores or hyphens."
        )
    title = _nonempty(str(form.get("title", "")), "Title")
    version = _nonempty(str(form.get("version", "")), "Version", 30)
    effective_date = str(form.get("effective_date", ""))
    try:
        date.fromisoformat(effective_date)
    except ValueError:
        raise HTTPException(422, "Use a valid effective date.")
    category = str(form.get("category", "Policy"))
    role_id = str(form.get("role_id", ""))
    if role_id and not request.app.state.db.job_roles.find_one({"_id": role_id}):
        raise HTTPException(422, "Unknown job role.")
    if category not in ["Policy", "SOP", "Role description", "FAQ", "Other"]:
        raise HTTPException(422, "Invalid category.")
    data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    try:
        record = ingest(
            request.app.state.db,
            settings,
            data,
            file.filename or "",
            {
                "document_id": document_id,
                "title": title,
                "version": version,
                "effective_date": effective_date,
                "category": category,
                "role_ids": [role_id] if role_id else [],
            },
            user["_id"],
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except Exception:
        raise HTTPException(
            422, "Unable to parse this document. Check the file and try again."
        ) from None
    return ok({"document": record}, 201)


@router.get("/documents/{document_id}")
def documents_detail(request: Request, document_id: str):
    require(request, EDITORS | REVIEWERS)
    db = request.app.state.db
    document = db.documents.find_one({"_id": document_id})
    if not document:
        raise HTTPException(404, "Document not found.")
    return ok(
        {
            "document": document,
            "sections": list(db.source_sections.find({"document_id": document_id})),
            "requirements": list(db.requirements.find({"document_id": document_id})),
            "roles": list(db.job_roles.find()),
            "jobs": list(db.jobs.find({"target_id": document_id}).sort("created_at", -1).limit(4)),
        }
    )


@router.post("/documents/{document_id}/activate")
def documents_activate(request: Request, document_id: str):
    user, session = require(request, REVIEWERS)
    api_csrf(request, session)
    db = request.app.state.db
    document = db.documents.find_one({"_id": document_id})
    if not document:
        raise HTTPException(404, "Document not found.")
    if document["suspicious"]:
        raise HTTPException(
            422, "Suspicious source instructions are quarantined. Upload a corrected source."
        )
    if date.fromisoformat(document["effective_date"]) > date.today():
        raise HTTPException(422, "A future-dated document cannot be active yet.")
    previous = list(
        db.documents.find(
            {
                "document_id": document["document_id"],
                "status": "active",
                "_id": {"$ne": document_id},
            }
        )
    )
    if any(d["effective_date"] >= document["effective_date"] for d in previous):
        raise HTTPException(409, "A newer or same-date active version exists.")
    db.documents.update_many(
        {"document_id": document["document_id"], "status": "active", "_id": {"$ne": document_id}},
        {"$set": {"status": "superseded"}},
    )
    db.documents.update_one(
        {"_id": document_id},
        {"$set": {"status": "active", "approved_by": user["_id"], "approved_at": now()}},
    )
    db.plans.update_many(
        {"source_document_ids": {"$in": [d["_id"] for d in previous]}},
        {"$set": {"status": "Stale sources"}},
    )
    audit(
        db,
        user["_id"],
        "document.activate",
        document_id,
        {"superseded": [d["_id"] for d in previous]},
    )
    return JSONResponse(None, status_code=204)


@router.post("/documents/{document_id}/extract")
def documents_extract(request: Request, document_id: str):
    user, session = require(request, EDITORS)
    api_csrf(request, session)
    document = request.app.state.db.documents.find_one({"_id": document_id})
    if not document:
        raise HTTPException(404, "Document not found.")
    if document["suspicious"]:
        raise HTTPException(422, "Quarantined source instructions cannot be sent for extraction.")
    job = enqueue(request.app.state.db, user["_id"], "extract", document_id)
    return ok({"job_id": job["_id"]}, 201)


class ReviewBody(BaseModel):
    title: str
    text: str
    mandatory: str = "false"
    due_stage: str
    role_id: str = ""
    decision: str


@router.post("/requirements/{requirement_id}/review")
def requirements_review(request: Request, requirement_id: str, body: ReviewBody):
    user, session = require(request, REVIEWERS)
    api_csrf(request, session)
    db = request.app.state.db
    req = db.requirements.find_one({"_id": requirement_id})
    if not req:
        raise HTTPException(404, "Requirement not found.")
    if body.decision not in ["approved", "rejected", "draft"] or body.due_stage not in STAGES:
        raise HTTPException(422, "Invalid review selection.")
    source = db.source_sections.find_one(
        {"document_id": req["document_id"], "section_id": req["section_id"]}
    )
    doc = db.documents.find_one({"_id": req["document_id"]})
    clean = normalized(body.text)
    if not clean or len(clean) > 6000 or clean not in normalized(source["text"]):
        raise HTTPException(
            422, "Requirement text must be an exact passage from its source section."
        )
    if body.decision == "approved" and (
        doc["status"] != "active" or doc["suspicious"] or SUSPICIOUS.search(clean)
    ):
        raise HTTPException(
            422, "Activate a safe source document before approving its requirements."
        )
    if body.role_id and not db.job_roles.find_one({"_id": body.role_id}):
        raise HTTPException(422, "Unknown job role.")
    changes = {
        "title": _nonempty(body.title, "Requirement title"),
        "text": clean,
        "mandatory": body.mandatory == "true",
        "due_stage": body.due_stage,
        "role_ids": [body.role_id] if body.role_id else [],
        "status": body.decision,
        "reviewed_by": user["_id"],
        "reviewed_at": now(),
    }
    db.requirements.update_one({"_id": requirement_id}, {"$set": changes})
    db.plans.update_many(
        {"source_document_ids": req["document_id"]}, {"$set": {"status": "Stale sources"}}
    )
    audit(
        db,
        user["_id"],
        "requirement.review",
        requirement_id,
        {"before": {k: req.get(k) for k in changes}, "after": changes},
    )
    return JSONResponse(None, status_code=204)


# ── Matrix ─────────────────────────────────────────────────────────────────────


@router.get("/matrix")
def matrix_page(request: Request):
    require(request, EDITORS | REVIEWERS)
    db = request.app.state.db
    roles = list(db.job_roles.find())
    role_id = request.query_params.get("role_id", roles[0]["_id"] if roles else "")
    return ok(
        {
            "roles": roles,
            "role_id": role_id,
            "requirements": matrix(db, role_id) if role_id else [],
        }
    )


# ── Jobs ───────────────────────────────────────────────────────────────────────


@router.get("/jobs/{job_id}")
def jobs_detail(request: Request, job_id: str):
    return ok({"job": _job_access(request, job_id)})


@router.get("/jobs/{job_id}/status")
def jobs_status(request: Request, job_id: str):
    job = _job_access(request, job_id)
    return ok({"status": job["status"]})


# ── Plans ──────────────────────────────────────────────────────────────────────


@router.get("/plans")
def plans_list(request: Request):
    user, _ = require(request)
    db = request.app.state.db
    employees = _employees_for(db, user)
    return ok(
        {
            "plans": list(
                db.plans.find(
                    {"employee_id": {"$in": [e["_id"] for e in employees]}}, {"matrix_snapshot": 0}
                )
                .sort("created_at", -1)
                .limit(100)
            ),
            "employees": {e["_id"]: e for e in employees},
        }
    )


@router.get("/plans/{plan_id}")
def plans_detail(request: Request, plan_id: str):
    from .training import current

    plan = _plan_access(request, plan_id)
    db = request.app.state.db
    employee = db.employees.find_one({"_id": plan["employee_id"]})
    user, _ = require(request)
    if user["role"] == "employee":
        plan["content"] = public_content(plan["content"])
    return ok(
        {
            "plan": plan,
            "employee": employee,
            "teaching": plan.get("learning_checks") or learning_checks(plan["content"]),
            "fresh": current(db, plan, employee),
            "decisions": list(db.plan_reviews.find({"plan_id": plan_id}).sort("created_at", 1)),
        }
    )


# ── Users (admin) ─────────────────────────────────────────────────────────────


@router.get("/users")
def users_list(request: Request):
    require(request, {"admin"})
    return ok(
        {
            "users": list(request.app.state.db.users.find({}, {"password_hash": 0})),
            "account_roles": sorted(ROLES),
        }
    )


class UserBody(BaseModel):
    email: str
    name: str
    password: str
    role: str


@router.post("/users")
def users_create(request: Request, body: UserBody):
    user, session = require(request, {"admin"})
    api_csrf(request, session)
    if body.role not in ROLES:
        raise HTTPException(422, "Invalid account role.")
    email = body.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
        raise HTTPException(422, "Enter a valid email address.")
    try:
        encoded = hash_password(body.password)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    key = uid()
    request.app.state.db.users.insert_one(
        {
            "_id": key,
            "email": email,
            "name": _nonempty(body.name, "Name"),
            "password_hash": encoded,
            "role": body.role,
            "active": True,
            "created_at": now(),
        }
    )
    audit(request.app.state.db, user["_id"], "user.create", key, {"role": body.role})
    return ok({"user": {"_id": key, "email": email, "name": body.name, "role": body.role}}, 201)


# ── Audit ──────────────────────────────────────────────────────────────────────


@router.get("/audit")
def audit_list(request: Request):
    require(request, REVIEWERS)
    return ok(
        {
            "events": list(
                request.app.state.db.audit_events.find().sort("created_at", -1).limit(100)
            ),
        }
    )
