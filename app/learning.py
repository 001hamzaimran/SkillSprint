"""Deterministic learning rules. No AI calls or automatic practical grading."""

from copy import deepcopy
from datetime import date, timedelta
from pydantic import ValidationError
from .schemas import FullOnboardingPlan, STAGES
from .ingestion import normalized

PASS_PERCENT = 80
STAGE_DAYS = dict(zip(STAGES, (0, 6, 13, 29, 59, 89)))


def learning_checks(content):
    try:
        plan = FullOnboardingPlan.model_validate(content)
    except ValidationError:
        return {
            "passed": False,
            "findings": [
                "Each module needs a lesson, checklist, scenario, valid quiz and scoring rubric. Regenerate legacy plans or correct the content."
            ],
        }
    findings = []
    for item in plan.items:
        if normalized(item.quiz.evidence_quote) != normalized(item.source_quote):
            findings.append(
                f"{item.requirement_id}: quiz evidence must match the approved policy quote."
            )
        if len(set(x.strip().casefold() for x in item.checklist)) != len(item.checklist):
            findings.append(f"{item.requirement_id}: checklist contains duplicate steps.")
        if not all(
            x.strip() for x in (item.module_title, item.learning_objective, item.practical_activity)
        ):
            findings.append(f"{item.requirement_id}: title, objective and activity are required.")
    return {"passed": not findings, "findings": findings}


def public_content(content):
    """Never send unattempted answer keys or model responses to an employee."""
    result = deepcopy(content)
    for item in result.get("items", []):
        if item.get("policy_facts"):
            item["policy_facts"].pop("answer_fact", None)
        if "quiz" in item:
            for key in ("correct_index", "explanation"):
                item["quiz"].pop(key, None)
        if "scenario" in item:
            item["scenario"].pop("expected_response", None)
    return result


def progress_report(db, plan, employee):
    query = {"plan_id": plan["_id"], "employee_id": employee["_id"]}
    records = {p["requirement_id"]: p for p in db.learning_progress.find(query)}
    attempts = list(db.quiz_attempts.find(query).sort("created_at", -1))
    submissions = list(db.practical_submissions.find(query).sort("created_at", -1))
    rows = []
    matrix = {r["requirement_id"]: r for r in plan.get("matrix_snapshot", [])}
    for item in plan["content"]["items"]:
        key = item["requirement_id"]
        saved = records.get(key, {})
        quizzes = [a for a in attempts if a["requirement_id"] == key]
        practicals = [s for s in submissions if s["requirement_id"] == key]
        quiz_passed = any(a["passed"] for a in quizzes)
        practical_passed = any(s.get("passed", False) for s in practicals)
        checklist_done = bool(item.get("checklist")) and set(saved.get("checked", [])) == set(
            range(len(item.get("checklist", [])))
        )
        complete = bool(
            saved.get("lesson_read") and checklist_done and quiz_passed and practical_passed
        )
        due = date.fromisoformat(employee["joining_date"]) + timedelta(
            days=STAGE_DAYS[item["stage"]]
        )
        latest = practicals[0] if practicals else None
        suggestion = ""
        if quizzes and not quiz_passed:
            suggestion = "Re-read the policy evidence and lesson, then retry the knowledge check."
        elif latest and latest["status"] == "graded" and not practical_passed:
            suggestion = (
                "Use your assessor’s feedback to revise the scenario and practical response."
            )
        rows.append(
            {
                "item": item,
                "saved": saved,
                "quiz_passed": quiz_passed,
                "practical_passed": practical_passed,
                "complete": complete,
                "checklist_done": checklist_done,
                "quiz_attempts": quizzes,
                "submissions": practicals,
                "latest_submission": latest,
                "due": due,
                "overdue": due < date.today() and not complete,
                "suggestion": suggestion,
                "competency": matrix.get(key, {}).get("competency") or item["module_title"],
            }
        )
    completed = {r["item"]["requirement_id"] for r in rows if r["complete"]}
    for row in rows:
        prerequisites = matrix.get(row["item"]["requirement_id"], {}).get("prerequisites", [])
        row["blocked_by"] = [key for key in prerequisites if key not in completed]
    required = [r for r in rows if r["item"]["mandatory"]]
    milestones = [
        {
            "stage": stage,
            "total": len([r for r in rows if r["item"]["stage"] == stage]),
            "completed": len([r for r in rows if r["item"]["stage"] == stage and r["complete"]]),
        }
        for stage in STAGES
    ]
    return {
        "rows": rows,
        "total": len(rows),
        "completed": len(completed),
        "percent": round(100 * len(completed) / len(rows)) if rows else 0,
        "mandatory_total": len(required),
        "mandatory_completed": sum(r["complete"] for r in required),
        "mandatory_complete": bool(required) and all(r["complete"] for r in required),
        "overdue": sum(r["overdue"] for r in rows),
        "weak": [r for r in rows if r["suggestion"]],
        "milestones": [m for m in milestones if m["total"]],
    }
