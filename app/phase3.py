"""Verification, policy change previews, controlled experiments and scoped reports."""

import csv
import io
import re
from copy import deepcopy
from fastapi import Request, Form, HTTPException
from fastapi.responses import Response, JSONResponse
from pydantic import ValidationError
from .db import now, uid, audit
from .security import require, csrf, EDITORS, REVIEWERS
from .schemas import PolicyRule
from .ingestion import normalized
from .policy import matrix_state, fingerprint, selective_delta, dependency_findings
from .worker import enqueue
from .training import go, text, current
from .learning import progress_report, public_content
from .comparison import compare_plans


def csv_response(filename, columns, rows):
    def safe(value):
        value = "" if value is None else str(value)
        return (
            "'" + value
            if value.lstrip().startswith(("=", "+", "-", "@"))
            or value.startswith(("\t", "\r", "\n"))
            else value
        )

    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([safe(value) for value in row])
    return Response(
        "\ufeff" + out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def install_phase3(app, page, employees_for, employee_access, plan_access):
    @app.get("/verification")
    def verification(request: Request):
        require(request, EDITORS | REVIEWERS)
        db = request.app.state.db
        roles = list(db.job_roles.find().sort("name", 1))
        role_id = request.query_params.get("role_id", roles[0]["_id"] if roles else "")
        state = matrix_state(db, role_id)
        return page(
            request,
            "verification.html",
            roles=roles,
            role_id=role_id,
            state=state,
            dependencies=dependency_findings(state["requirements"]),
            annotated=sum(bool(r.get("policy_rule")) for r in state["requirements"]),
        )

    @app.post("/requirements/{requirement_id}/rules")
    async def annotate(request: Request, requirement_id: str):
        user, session = require(request, REVIEWERS)
        form = await request.form()
        csrf(request, session, str(form.get("csrf_token", "")))
        db = request.app.state.db
        req = db.requirements.find_one({"_id": requirement_id})
        if not req:
            raise HTTPException(404, "Requirement not found.")
        key = str(form.get("key", "")).strip().lower()
        rule = None
        if key:
            if not re.fullmatch(r"[a-z0-9_.-]{2,80}", key):
                raise HTTPException(
                    422,
                    "Rule key must use 2–80 lowercase letters, numbers, periods, underscores or hyphens.",
                )
            fields = {
                k: str(form.get(k, "")).strip()
                for k in (
                    "value",
                    "condition",
                    "exception",
                    "answer_fact",
                    "module_category",
                    "assessment_topic",
                )
            }
            try:
                rule = PolicyRule(key=key, **fields).model_dump()
            except ValidationError:
                raise HTTPException(
                    422,
                    "Provide a rule value, module category and assessment topic within the displayed limits.",
                ) from None
            for field in ("value", "condition", "exception", "answer_fact"):
                if rule[field] and normalized(rule[field]) not in normalized(req["text"]):
                    raise HTTPException(
                        422,
                        f'{field.replace("_"," ").capitalize()} must be an exact excerpt of the approved requirement text.',
                    )
        deps = list(
            dict.fromkeys(
                x.strip() for x in str(form.get("prerequisites", "")).split(",") if x.strip()
            )
        )
        if len(deps) > 20 or req["requirement_id"] in deps:
            raise HTTPException(
                422, "Choose at most 20 prerequisites, excluding this requirement itself."
            )
        if db.requirements.count_documents(
            {"requirement_id": {"$in": deps}, "status": "approved"}
        ) != len(deps):
            raise HTTPException(
                422, "Prerequisites must reference existing approved requirement IDs."
            )
        reason = text(form.get("reason", ""), "Review reason", 2000)
        db.requirements.update_one(
            {"_id": req["_id"]},
            {
                "$set": {
                    "policy_rule": rule,
                    "prerequisites": deps,
                    "rules_reviewed_by": user["_id"],
                    "rules_reviewed_at": now(),
                }
            },
        )
        db.plans.update_many(
            {"source_document_ids": req["document_id"]}, {"$set": {"status": "Stale sources"}}
        )
        audit(
            db,
            user["_id"],
            "requirement.rules",
            req["_id"],
            {
                "before": req.get("policy_rule"),
                "after": rule,
                "prerequisites": deps,
                "reason": reason,
            },
        )
        return go(
            "/documents/" + req["document_id"],
            "Reviewed rule metadata saved. Related plans need revalidation or updating.",
        )

    @app.post("/verification/{role_id}/resolve")
    def resolve(
        request: Request,
        role_id: str,
        conflict_id: str = Form(...),
        winner_id: str = Form(...),
        reason: str = Form(...),
        csrf_token: str = Form(...),
    ):
        user, session = require(request, REVIEWERS)
        csrf(request, session, csrf_token)
        db = request.app.state.db
        group = next(
            (g for g in matrix_state(db, role_id)["conflicts"] if g["_id"] == conflict_id), None
        )
        if not group or winner_id not in {r["requirement_id"] for r in group["requirements"]}:
            raise HTTPException(
                409, "The conflict changed. Refresh and review the current rule versions."
            )
        reason = text(reason, "Precedence reason", 2000)
        record = {
            "_id": conflict_id,
            "role_id": role_id,
            "winner_id": winner_id,
            "reason": reason,
            "actor_id": user["_id"],
            "created_at": now(),
        }
        db.conflict_resolutions.replace_one({"_id": conflict_id}, record, upsert=True)
        db.plans.update_many({"role_id": role_id}, {"$set": {"status": "Stale sources"}})
        audit(db, user["_id"], "policy.resolve", conflict_id, record)
        return go("/verification?role_id=" + role_id)

    @app.get("/documents/{document_id}/impact")
    def document_impact(request: Request, document_id: str):
        require(request, EDITORS | REVIEWERS)
        db = request.app.state.db
        document = db.documents.find_one({"_id": document_id})
        if not document:
            raise HTTPException(404, "Document not found.")
        previous = list(
            db.documents.find(
                {
                    "document_id": document["document_id"],
                    "status": "active",
                    "_id": {"$ne": document_id},
                }
            )
        )
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
                affected.append(
                    {
                        "employee": employee,
                        "plan": plan,
                        "items": items,
                        "checklists": sum(len(i.get("checklist", [])) for i in items),
                        "quizzes": sum(bool(i.get("quiz")) for i in items),
                    }
                )
        return page(
            request,
            "impact.html",
            document=document,
            previous=previous,
            affected=affected,
            old_requirements=list(db.requirements.find({"document_id": {"$in": oldids}})),
            new_requirements=list(db.requirements.find({"document_id": document_id})),
        )

    @app.get("/plans/{plan_id}/update")
    def update_preview(request: Request, plan_id: str):
        require(request, EDITORS | REVIEWERS)
        plan = plan_access(request, plan_id)
        db = request.app.state.db
        employee = db.employees.find_one({"_id": plan["employee_id"]})
        state = matrix_state(db, employee["role_id"])
        delta = selective_delta(
            plan,
            state["requirements"],
            {k: employee[k] for k in ("role_id", "department", "experience", "joining_date")},
        )
        return page(
            request,
            "update_plan.html",
            plan=plan,
            delta=delta,
            state=state,
            employee=employee,
            old={r["requirement_id"]: r for r in plan.get("matrix_snapshot", [])},
            new={r["requirement_id"]: r for r in state["requirements"]},
        )

    @app.post("/plans/{plan_id}/update")
    def selective(request: Request, plan_id: str, csrf_token: str = Form(...)):
        user, session = require(request, EDITORS | REVIEWERS)
        csrf(request, session, csrf_token)
        plan = plan_access(request, plan_id)
        db = request.app.state.db
        employee = db.employees.find_one({"_id": plan["employee_id"]})
        if employee.get("active_plan_id") != plan_id or not plan.get("published_at"):
            raise HTTPException(
                409, "Choose the currently assigned published plan as the update baseline."
            )
        state = matrix_state(db, employee["role_id"])
        if state["unresolved"]:
            raise HTTPException(409, "Resolve rule conflicts before selectively updating the plan.")
        if not state["requirements"]:
            raise HTTPException(
                409,
                "No approved requirements remain. Review the assignment instead of generating empty training.",
            )
        job = enqueue(db, user["_id"], "selective", plan["employee_id"], base_plan_id=plan_id)
        return go("/jobs/" + job["_id"])

    @app.get("/plans/{plan_id}/compare")
    def compare(request: Request, plan_id: str):
        plan = plan_access(request, plan_id)
        db = request.app.state.db
        user, _ = require(request)
        alternatives = list(
            db.plans.find({"employee_id": plan["employee_id"], "_id": {"$ne": plan_id}})
            .sort("created_at", -1)
            .limit(100)
        )
        other_id = request.query_params.get("other", alternatives[0]["_id"] if alternatives else "")
        other = plan_access(request, other_id) if other_id else None
        if other and other["employee_id"] != plan["employee_id"]:
            raise HTTPException(422, "Compare versions for the same employee.")
        if user["role"] == "employee":
            plan["content"] = public_content(plan["content"])
            if other:
                other["content"] = public_content(other["content"])
        return page(
            request,
            "compare.html",
            left=plan,
            right=other,
            alternatives=alternatives,
            comparison=compare_plans(plan, other) if other else None,
        )

    @app.post("/plans/{plan_id}/consistency")
    def start_experiment(request: Request, plan_id: str, csrf_token: str = Form(...)):
        user, session = require(request, EDITORS | REVIEWERS)
        csrf(request, session, csrf_token)
        plan = plan_access(request, plan_id)
        db = request.app.state.db
        employee = db.employees.find_one({"_id": plan["employee_id"]})
        state = matrix_state(db, employee["role_id"])
        if not state["requirements"] or state["unresolved"]:
            raise HTTPException(409, "Approve a non-conflicting role matrix first.")
        # Two runs are explicit in the button label; stored as real generation jobs.
        key = uid()
        digest = fingerprint(state["requirements"])
        context = {k: employee[k] for k in ("role_id", "department", "experience", "joining_date")}
        jobs = [
            enqueue(
                db,
                user["_id"],
                "generate",
                employee["_id"],
                experiment_id=key,
                expected_snapshot=digest,
                expected_context=context,
                expected_model=request.app.state.settings.genai_model,
            )["_id"]
            for _ in range(2)
        ]
        db.consistency_experiments.insert_one(
            {
                "_id": key,
                "employee_id": employee["_id"],
                "actor_id": user["_id"],
                "snapshot_digest": digest,
                "employee_snapshot": context,
                "job_ids": jobs,
                "created_at": now(),
            }
        )
        audit(db, user["_id"], "consistency.start", key, {"job_ids": jobs})
        return go("/experiments/" + key)

    @app.get("/experiments/{experiment_id}")
    def experiment(request: Request, experiment_id: str):
        require(request, EDITORS | REVIEWERS)
        db = request.app.state.db
        record = db.consistency_experiments.find_one({"_id": experiment_id})
        if not record:
            raise HTTPException(404, "Experiment not found.")
        employee_access(request, record["employee_id"])
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
        return page(
            request,
            "experiment.html",
            experiment=record,
            jobs=jobs,
            plans=plans,
            comparison=comparison,
        )

    def report_rows(request):
        user, _ = require(request)
        db = request.app.state.db
        employees = {e["_id"]: e for e in employees_for(db, user)}
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
            rows.append(
                {
                    "plan": plan,
                    "employee": employee,
                    "progress": report,
                    "current": current(db, plan, employee, role_states[employee["role_id"]]),
                    "assigned": employee.get("active_plan_id") == plan["_id"],
                }
            )
        return rows

    @app.get("/reports")
    def reports(request: Request):
        rows = report_rows(request)
        return page(
            request,
            "reports.html",
            rows=rows,
            q=request.query_params.get("q", ""),
            role_id=request.query_params.get("role_id", ""),
            selected_status=request.query_params.get("status", ""),
            roles=list(request.app.state.db.job_roles.find()),
        )

    @app.get("/reports.csv")
    def export_reports(request: Request):
        rows = report_rows(request)
        return csv_response(
            "skillsprint-progress.csv",
            [
                "Employee",
                "Role",
                "Plan",
                "Status",
                "Assigned",
                "Sources current",
                "Coverage %",
                "Traceability %",
                "Learning %",
                "Mandatory completed",
                "Mandatory total",
                "Overdue",
                "Weak areas",
            ],
            [
                [
                    r["employee"]["name"],
                    r["employee"]["role_name"],
                    r["plan"]["content"]["title"],
                    r["plan"]["status"],
                    r["assigned"],
                    r["current"],
                    r["plan"]["validation"]["coverage"],
                    r["plan"]["validation"]["traceability"],
                    r["progress"]["percent"],
                    r["progress"]["mandatory_completed"],
                    r["progress"]["mandatory_total"],
                    r["progress"]["overdue"],
                    len(r["progress"]["weak"]),
                ]
                for r in rows
            ],
        )

    @app.get("/plans/{plan_id}/validation.csv")
    def validation_csv(request: Request, plan_id: str):
        plan = plan_access(request, plan_id)
        rows = [
            [
                r["requirement_id"],
                r["result"],
                r["expected_text"],
                r["actual_text"],
                "; ".join(r["errors"]),
            ]
            for r in plan["validation"]["rows"]
        ]
        rows.extend(
            [
                [f.get("requirement_id", ""), "Finding", "", "", f["code"] + ": " + f["message"]]
                for f in plan["validation"]["findings"]
            ]
        )
        rows.extend(
            [
                [
                    f.get("requirement_id", ""),
                    "Review warning",
                    "",
                    "",
                    f["code"] + ": " + f["message"],
                ]
                for f in plan["validation"].get("warnings", [])
            ]
        )
        return csv_response(
            "skillsprint-validation.csv",
            ["Requirement", "Result", "Expected policy", "Generated policy quote", "Findings"],
            rows,
        )

    @app.get("/experiments/{experiment_id}/json")
    def experiment_json(request: Request, experiment_id: str):
        require(request, EDITORS | REVIEWERS)
        db = request.app.state.db
        record = db.consistency_experiments.find_one({"_id": experiment_id})
        if not record:
            raise HTTPException(404, "Experiment not found.")
        employee_access(request, record["employee_id"])
        jobs = list(db.jobs.find({"_id": {"$in": record["job_ids"]}}))
        plans = [db.plans.find_one({"_id": j.get("result_id")}) for j in jobs]
        if not all(plans) or len(plans) != 2:
            raise HTTPException(409, "Both generation runs must finish before comparison export.")
        report = compare_plans(*plans)
        report.pop("rows")
        return JSONResponse(
            {
                "experiment_id": experiment_id,
                "plan_ids": [p["_id"] for p in plans],
                "snapshot_digest": record["snapshot_digest"],
                "comparison": report,
                "generation": [p["generation"] for p in plans],
            },
            headers={"Content-Disposition": 'attachment; filename="consistency.json"'},
        )
