"""Review, publication, learner work and human assessment routes."""

from copy import deepcopy
from urllib.parse import quote
from fastapi import Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from .db import uid, now, audit
from .security import require, csrf, EDITORS, REVIEWERS
from .schemas import FullOnboardingPlan, FullLearningItem
from .learning import learning_checks, progress_report, public_content, PASS_PERCENT
from .validation import validate_plan
from .worker import matrix, fingerprint, enqueue
from .updates import carry_progress, serialized_learning
from .policy import matrix_state


def go(path, message=""):
    return RedirectResponse(
        path + ("?message=" + quote(message) if message else ""), status_code=303
    )


def text(value, label, limit=5000):
    value = str(value).strip()
    if not value or len(value) > limit:
        raise HTTPException(422, f"{label} is required and must be at most {limit} characters.")
    return value


def current(db, plan, employee, role_state=None):
    role_state = role_state if role_state is not None else matrix_state(db, employee["role_id"])
    return (
        plan["status"] != "Stale sources"
        and plan["role_id"] == employee["role_id"]
        and all(employee.get(k) == v for k, v in plan.get("employee_snapshot", {}).items())
        and not role_state["unresolved"]
        and plan.get("snapshot_digest") == fingerprint(role_state["requirements"])
    )


def inspect_plan(db, content, employee):
    try:
        parsed = FullOnboardingPlan.model_validate(content)
    except ValidationError:
        raise HTTPException(
            422,
            "The plan needs complete Phase 2 lessons and assessments. Regenerate the plan or correct its content.",
        ) from None
    requirements = matrix(db, employee["role_id"])
    ids = list({r["document_id"] for r in requirements})
    validation = validate_plan(
        parsed,
        requirements,
        list(db.documents.find({"_id": {"$in": ids}})),
        list(db.source_sections.find({"document_id": {"$in": ids}})),
        employee["role_id"],
    )
    return validation, learning_checks(content), requirements


def install_training(app, page, employees_for, employee_access, plan_access):
    def context(request, plan_id, active=False):
        plan = plan_access(request, plan_id)
        user, session, employee = employee_access(request, plan["employee_id"])
        db = request.app.state.db
        fresh = current(db, plan, employee)
        if active and (
            plan["status"] != "Published" or employee.get("active_plan_id") != plan_id or not fresh
        ):
            raise HTTPException(
                409,
                "This is not the current published plan, or its sources changed. Ask a reviewer to publish an up-to-date plan.",
            )
        return db, plan, employee, user, session, fresh

    def learner_item(request, plan_id, requirement_id, token):
        db, plan, employee, user, session, _ = context(request, plan_id, active=True)
        csrf(request, session, token)
        if user["role"] != "employee" or employee.get("user_id") != user["_id"]:
            raise HTTPException(403, "Only the assigned employee can submit learning work.")
        report = progress_report(db, plan, employee)
        row = next(
            (r for r in report["rows"] if r["item"]["requirement_id"] == requirement_id), None
        )
        if not row:
            raise HTTPException(404, "Learning item not found.")
        if row["blocked_by"]:
            raise HTTPException(
                409, "Complete prerequisite modules first: " + ", ".join(row["blocked_by"])
            )
        return db, plan, employee, user, row

    @app.get("/learning")
    def learning_home(request: Request):
        user, _ = require(request)
        db = request.app.state.db
        cards = []
        for employee in employees_for(db, user):
            plan = db.plans.find_one({"_id": employee.get("active_plan_id", "")})
            cards.append(
                {
                    "employee": employee,
                    "plan": plan,
                    "fresh": current(db, plan, employee) if plan else False,
                    "report": progress_report(db, plan, employee) if plan else None,
                }
            )
        return page(request, "learning_home.html", cards=cards)

    @app.get("/learning/{plan_id}")
    def learn(request: Request, plan_id: str):
        db, plan, employee, user, _, fresh = context(request, plan_id)
        report = progress_report(db, plan, employee)
        active = (
            plan["status"] == "Published" and employee.get("active_plan_id") == plan_id and fresh
        )
        if user["role"] == "employee":
            for row in report["rows"]:
                row["item"] = public_content({"items": [row["item"]]})["items"][0]
        return page(
            request,
            "learn.html",
            plan=plan,
            employee=employee,
            report=report,
            active=active,
            is_learner=user["role"] == "employee",
            pass_percent=PASS_PERCENT,
        )

    @app.post("/plans/{plan_id}/review")
    @serialized_learning
    def review(
        request: Request,
        plan_id: str,
        decision: str = Form(...),
        comment: str = Form(...),
        confirmed: str = Form(""),
        csrf_token: str = Form(...),
    ):
        user, session = require(request, REVIEWERS)
        csrf(request, session, csrf_token)
        db, plan, employee, _, _, fresh = context(request, plan_id)
        if decision not in ["approve", "reject", "comment"]:
            raise HTTPException(422, "Choose a valid review action.")
        comment = text(comment, "Review comment", 3000)
        if decision != "comment":
            if plan["status"] == "Published":
                raise HTTPException(
                    409,
                    "Published content is immutable. Create an edited draft for another decision.",
                )
            if decision == "approve":
                if confirmed != "true":
                    raise HTTPException(
                        422,
                        "Confirm that you reviewed lessons, quiz answers, scenarios and rubrics against their sources.",
                    )
                validation, teaching, requirements = inspect_plan(db, plan["content"], employee)
                if not fresh or not validation["core_passed"] or not teaching["passed"]:
                    raise HTTPException(
                        409,
                        "Resolve validation findings and stale sources before publishing. No override can bypass these checks.",
                    )
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
                raise HTTPException(
                    409, "Another reviewer changed this plan. Refresh before deciding."
                )
            if decision == "approve":
                # This single employee pointer is the authority for active learning.
                db.employees.update_one(
                    {"_id": employee["_id"]}, {"$set": {"active_plan_id": plan_id}}
                )
        db.plan_reviews.insert_one(
            {
                "_id": uid(),
                "plan_id": plan_id,
                "actor_id": user["_id"],
                "actor_name": user["name"],
                "decision": decision,
                "comment": comment,
                "created_at": now(),
            }
        )
        audit(db, user["_id"], "plan." + decision, plan_id, {"comment": comment})
        return go(
            "/plans/" + plan_id,
            "Review saved."
            + (" The plan is now assigned to this employee." if decision == "approve" else ""),
        )

    @app.post("/plans/{plan_id}/regenerate")
    def regenerate(request: Request, plan_id: str, csrf_token: str = Form(...)):
        user, session = require(request, EDITORS | REVIEWERS)
        csrf(request, session, csrf_token)
        plan = plan_access(request, plan_id)
        job = enqueue(request.app.state.db, user["_id"], "generate", plan["employee_id"])
        return go("/jobs/" + job["_id"])

    @app.get("/plans/{plan_id}/items/{requirement_id}/edit")
    def edit_page(request: Request, plan_id: str, requirement_id: str):
        require(request, EDITORS | REVIEWERS)
        plan = plan_access(request, plan_id)
        item = next(
            (i for i in plan["content"]["items"] if i["requirement_id"] == requirement_id), None
        )
        if not item:
            raise HTTPException(404, "Learning item not found.")
        if "quiz" not in item:
            raise HTTPException(409, "Regenerate this legacy plan to add Phase 2 content first.")
        return page(request, "edit_item.html", plan=plan, item=item)

    @app.post("/plans/{plan_id}/items/{requirement_id}/edit")
    async def edit_item(request: Request, plan_id: str, requirement_id: str):
        user, session = require(request, EDITORS | REVIEWERS)
        form = await request.form()
        csrf(request, session, str(form.get("csrf_token", "")))
        db, plan, employee, _, _, fresh = context(request, plan_id)
        if not fresh:
            raise HTTPException(
                409, "Sources changed. Regenerate against the current matrix before editing."
            )
        content = deepcopy(plan["content"])
        item = next((i for i in content["items"] if i["requirement_id"] == requirement_id), None)
        if not item or "quiz" not in item:
            raise HTTPException(404, "Phase 2 learning item not found.")
        for field in [
            "module_title",
            "learning_objective",
            "lesson",
            "practical_activity",
            "stage",
        ]:
            item[field] = text(form.get(field, ""), field.replace("_", " "))
        try:
            item["estimated_minutes"] = int(str(form.get("estimated_minutes", "")))
            item["checklist"] = [
                x.strip() for x in str(form.get("checklist", "")).splitlines() if x.strip()
            ]
            item["scenario"] = {
                "prompt": text(form.get("scenario_prompt", ""), "Scenario"),
                "expected_response": text(
                    form.get("scenario_expected", ""), "Expected scenario response"
                ),
            }
            item["quiz"] = {
                "question": text(form.get("question", ""), "Quiz question"),
                "options": [
                    x.strip() for x in str(form.get("options", "")).splitlines() if x.strip()
                ],
                "correct_index": int(str(form.get("correct_index", ""))),
                "explanation": text(form.get("explanation", ""), "Answer explanation"),
                "evidence_quote": item["source_quote"],
            }
            item["rubric"] = [
                {
                    "criterion": text(form.get("criterion_" + str(i), ""), "Rubric criterion"),
                    "max_points": int(str(form.get("points_" + str(i), ""))),
                }
                for i in range(len(item["rubric"]))
            ]
            FullLearningItem.model_validate(item)
        except (ValueError, ValidationError):
            raise HTTPException(
                422,
                "Check the quiz options and correct-answer index, checklist, stage, minutes and rubric point limits.",
            ) from None
        reason = text(form.get("reason", ""), "Edit reason", 3000)
        validation, teaching, requirements = inspect_plan(db, content, employee)
        key = uid()
        new = {
            k: deepcopy(plan[k])
            for k in (
                "employee_id",
                "role_id",
                "source_document_ids",
                "model",
                "prompt_version",
                "generation",
            )
        }
        new.update(
            {
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
            }
        )
        db.plans.insert_one(new)
        db.plan_reviews.insert_one(
            {
                "_id": uid(),
                "plan_id": key,
                "actor_id": user["_id"],
                "actor_name": user["name"],
                "decision": "edit",
                "comment": reason,
                "created_at": now(),
            }
        )
        audit(
            db,
            user["_id"],
            "plan.edit",
            key,
            {"parent_plan_id": plan_id, "requirement_id": requirement_id, "reason": reason},
        )
        return go(
            "/plans/" + key,
            "Edited draft created and revalidated. The original plan and its learner history are preserved.",
        )

    @app.post("/learning/{plan_id}/{requirement_id}/progress")
    @serialized_learning
    async def save_progress(request: Request, plan_id: str, requirement_id: str):
        form = await request.form()
        db, plan, employee, user, row = learner_item(
            request, plan_id, requirement_id, str(form.get("csrf_token", ""))
        )
        try:
            checked = sorted(set(int(x) for x in form.getlist("checked")))
        except ValueError:
            raise HTTPException(422, "Invalid checklist selection.") from None
        if any(i < 0 or i >= len(row["item"]["checklist"]) for i in checked):
            raise HTTPException(422, "Checklist entry does not exist.")
        key = {"plan_id": plan_id, "employee_id": employee["_id"], "requirement_id": requirement_id}
        db.learning_progress.update_one(
            key,
            {
                "$set": {
                    "checked": checked,
                    "lesson_read": form.get("lesson_read") == "true",
                    "updated_at": now(),
                },
                "$setOnInsert": {"_id": uid(), **key},
            },
            upsert=True,
        )
        audit(db, user["_id"], "learning.progress", plan_id, {"requirement_id": requirement_id})
        return go("/learning/" + plan_id + "#" + requirement_id)

    @app.post("/learning/{plan_id}/{requirement_id}/quiz")
    @serialized_learning
    def quiz(
        request: Request,
        plan_id: str,
        requirement_id: str,
        answer: int = Form(...),
        csrf_token: str = Form(...),
    ):
        db, plan, employee, user, row = learner_item(request, plan_id, requirement_id, csrf_token)
        question = row["item"]["quiz"]
        if not 0 <= answer < len(question["options"]):
            raise HTTPException(422, "Select an existing answer.")
        passed = answer == question["correct_index"]
        db.quiz_attempts.insert_one(
            {
                "_id": uid(),
                "plan_id": plan_id,
                "employee_id": employee["_id"],
                "requirement_id": requirement_id,
                "answer": answer,
                "score": 100 if passed else 0,
                "passed": passed,
                "feedback": question["explanation"],
                "created_at": now(),
            }
        )
        audit(
            db,
            user["_id"],
            "learning.quiz",
            plan_id,
            {"requirement_id": requirement_id, "score": 100 if passed else 0},
        )
        return go("/learning/" + plan_id + "#" + requirement_id)

    @app.post("/learning/{plan_id}/{requirement_id}/submit")
    @serialized_learning
    def submit(
        request: Request,
        plan_id: str,
        requirement_id: str,
        scenario_response: str = Form(...),
        practical_response: str = Form(...),
        csrf_token: str = Form(...),
    ):
        db, plan, employee, user, row = learner_item(request, plan_id, requirement_id, csrf_token)
        if row["practical_passed"] or (
            row["latest_submission"] and row["latest_submission"]["status"] == "pending"
        ):
            raise HTTPException(
                409, "This activity already passed or has a submission awaiting assessment."
            )
        key = uid()
        db.practical_submissions.insert_one(
            {
                "_id": key,
                "plan_id": plan_id,
                "employee_id": employee["_id"],
                "requirement_id": requirement_id,
                "status": "pending",
                "scenario_response": text(scenario_response, "Scenario response"),
                "practical_response": text(practical_response, "Practical response"),
                "created_at": now(),
            }
        )
        audit(db, user["_id"], "learning.submit", key)
        return go("/learning/" + plan_id + "#" + requirement_id)

    @app.get("/assessments")
    def assessment_queue(request: Request):
        user, _ = require(request, REVIEWERS | {"manager"})
        db = request.app.state.db
        employees = {e["_id"]: e for e in employees_for(db, user)}
        submissions = list(
            db.practical_submissions.find(
                {
                    "employee_id": {"$in": list(employees)},
                    "plan_id": {"$in": [e.get("active_plan_id", "") for e in employees.values()]},
                    "status": "pending",
                }
            ).sort("created_at", 1)
        )
        return page(request, "assessments.html", submissions=submissions, employees=employees)

    @app.post("/submissions/{submission_id}/grade")
    @serialized_learning
    async def grade(request: Request, submission_id: str):
        user, session = require(request, REVIEWERS | {"manager"})
        form = await request.form()
        csrf(request, session, str(form.get("csrf_token", "")))
        db = request.app.state.db
        submission = db.practical_submissions.find_one({"_id": submission_id})
        if not submission:
            raise HTTPException(404, "Submission not found.")
        db, plan, employee, _, _, _ = context(request, submission["plan_id"], active=True)
        item = next(
            i
            for i in plan["content"]["items"]
            if i["requirement_id"] == submission["requirement_id"]
        )
        try:
            scores = [int(str(form.get("score_" + str(i), ""))) for i in range(len(item["rubric"]))]
        except ValueError:
            raise HTTPException(
                422, "Provide whole-number scores for every rubric criterion."
            ) from None
        if any(
            score < 0 or score > rule["max_points"] for score, rule in zip(scores, item["rubric"])
        ):
            raise HTTPException(422, "Scores must be within the rubric limits.")
        maximum = sum(r["max_points"] for r in item["rubric"])
        percent = round(100 * sum(scores) / maximum, 1)
        feedback = text(form.get("feedback", ""), "Assessor feedback", 3000)
        result = db.practical_submissions.update_one(
            {"_id": submission_id, "status": "pending"},
            {
                "$set": {
                    "status": "graded",
                    "scores": scores,
                    "maximum": maximum,
                    "percent": percent,
                    "passed": 100 * sum(scores) >= PASS_PERCENT * maximum,
                    "feedback": feedback,
                    "graded_by": user["_id"],
                    "graded_at": now(),
                }
            },
        )
        if not result.matched_count:
            raise HTTPException(409, "This submission was already graded. Its result is preserved.")
        audit(
            db,
            user["_id"],
            "learning.grade",
            submission_id,
            {"scores": scores, "percent": percent, "feedback": feedback},
        )
        return go("/learning/" + plan["_id"] + "#" + submission["requirement_id"])

    @app.post("/employees/{employee_id}/account")
    def link_account(
        request: Request, employee_id: str, user_id: str = Form(""), csrf_token: str = Form(...)
    ):
        user, session = require(request, EDITORS)
        csrf(request, session, csrf_token)
        _, _, employee = employee_access(request, employee_id)
        db = request.app.state.db
        if user_id and not db.users.find_one({"_id": user_id, "role": "employee", "active": True}):
            raise HTTPException(422, "Choose an active employee login.")
        db.employees.update_one({"_id": employee_id}, {"$set": {"user_id": user_id}})
        audit(
            db,
            user["_id"],
            "employee.link_account",
            employee_id,
            {"previous": employee.get("user_id", ""), "user_id": user_id},
        )
        return go("/employees", "Employee login updated.")
