from copy import deepcopy
from urllib.parse import urlsplit, parse_qs

import pytest
from pydantic import ValidationError

from app.schemas import QuizQuestion
from app.learning import quiz_result, STAGE_DAYS
from app.workspace_api import evaluate_progress
from app.worker import enqueue, process_one
from app.schemas import Extraction
from app.policy import matrix
from .test_phase2 import training


def sign_in(client, role="admin"):
    result = client.post(
        "/api/auth/login", json={"email": role + "@test.local", "password": "Test-password-123!"}
    )
    assert result.status_code == 200
    return {"X-CSRF-Token": result.json()["csrf_token"]}


def test_question_types_and_exact_set_scoring():
    base = {
        "question": "Choose safe actions",
        "options": ["Lock the screen", "Share a password", "Report the incident"],
        "correct_index": 0,
        "explanation": "Follow the source.",
        "evidence_quote": "Lock the screen and report the incident.",
    }
    multiple = QuizQuestion(**base, question_type="multiple_response", correct_indices=[0, 2])
    assert quiz_result(multiple.model_dump(), [2, 0])
    assert not quiz_result(multiple.model_dump(), [0])
    assert not quiz_result(multiple.model_dump(), [0, 1, 2])
    with pytest.raises(ValidationError):
        QuizQuestion(**base, question_type="multiple_response", correct_indices=[9])
    boolean = {**base, "options": ["True", "False"], "question_type": "true_false"}
    assert quiz_result(QuizQuestion(**boolean).model_dump(), [0])
    with pytest.raises(ValidationError):
        QuizQuestion(**base, question_type="true_false")


def test_origin_schedule_and_password_reset(workspace):
    client, db, settings = workspace
    rejected = client.post(
        "/api/auth/login",
        headers={"Origin": "https://attacker.example"},
        json={"email": "admin@test.local", "password": "Test-password-123!"},
    )
    assert rejected.status_code == 403
    allowed = client.options(
        "/api/auth/login",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    headers = sign_in(client)
    days = {**STAGE_DAYS, "First 90 Days": 100}
    assert (
        client.put("/api/settings/stages", headers=headers, json={"days": days}).status_code == 200
    )
    assert client.get("/api/settings/stages").json()["days"] == days
    assert (
        client.put("/api/settings/stages", headers=headers, json={"days": {"Day 1": 0}}).status_code
        == 422
    )
    response = client.post("/api/auth/forgot-password", json={"email": "admin@test.local"})
    token = parse_qs(urlsplit(response.json()["development_reset_url"]).query)["token"][0]
    assert (
        client.post(
            "/api/auth/reset-password", json={"token": token, "password": "Updated-test-password!"}
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me").status_code == 401
    assert (
        client.post(
            "/api/auth/reset-password", json={"token": token, "password": "Updated-test-password!"}
        ).status_code
        == 422
    )
    settings.app_env = "production"
    assert (
        "development_reset_url"
        not in client.post("/api/auth/forgot-password", json={"email": "admin@test.local"}).json()
    )


def test_review_queue_overrides_search_management_and_redaction(training):
    client, db, _, plan, _ = training
    headers = sign_in(client)
    assert client.get("/api/review-queue").json()["plans"]
    warning = plan["validation"]["warnings"][0]
    path = f"/api/plans/{plan['_id']}/overrides"
    body = {
        "code": warning["code"],
        "requirement_id": warning.get("requirement_id", ""),
        "reason": "Reviewer checked the original source and accepts this advisory.",
    }
    assert client.post(path, headers=headers, json=body).status_code == 201
    assert (
        client.post(path, headers=headers, json={**body, "code": "REQUIREMENT_MISSING"}).status_code
        == 422
    )
    assert db.plans.find_one({"_id": plan["_id"]})["validation"] == plan["validation"]
    assert db.plan_reviews.find_one({"decision": "override"})["original_result"] == warning
    assert client.get("/api/search?q=workstation").json()["modules"]
    role = client.put(
        "/api/roles/role",
        headers=headers,
        json={"name": "Support team", "department": "Support", "description": "Customer support"},
    ).json()["role"]
    assert role["name"] == "Support team"
    duplicate = deepcopy(plan)
    duplicate["_id"] = "second-plan"
    db.plans.insert_one(duplicate)
    assert (
        client.get(
            "/api/compare", params={"left": plan["_id"], "right": duplicate["_id"]}
        ).status_code
        == 200
    )
    user_headers = sign_in(client, "employee")
    assert client.get("/api/review-queue").status_code == 403
    assert (
        client.put(
            "/api/settings/stages", headers=user_headers, json={"days": STAGE_DAYS}
        ).status_code
        == 403
    )
    for route in [
        "/api/dashboard",
        "/api/plans",
        "/api/reports",
        "/api/learning",
        "/api/search?q=workstation",
        f"/api/learning/{plan['_id']}",
    ]:
        response = client.get(route)
        assert response.status_code == 200, route
        assert "correct_index" not in response.text, route
        assert "expected_response" not in response.text, route
        assert "password_hash" not in response.text, route


def test_stage_snapshot_and_periodic_progress(training):
    client, db, _, plan, _ = training
    days = {**STAGE_DAYS, "Week 1": 7}
    db.plans.update_one({"_id": plan["_id"]}, {"$set": {"stage_days": days}})
    db.employees.update_one({"_id": "learner"}, {"$set": {"active_plan_id": plan["_id"]}})
    evaluate_progress(db)
    result = db.progress_evaluations.find_one({"_id": "learner"})
    assert result["status"] == "Behind Schedule"
    assert result["recommendations"]
    sign_in(client)
    insights = client.get("/api/insights").json()
    assert insights["roles"][0]["average_progress"] == 0
    assert insights["people"][0]["status"] == "Behind Schedule"


def test_review_classification_and_prerequisite_suggestions(training):
    client, db, settings, plan, _ = training
    headers = sign_in(client)
    requirement = db.requirements.find_one({"status": "approved"})
    review = {
        "title": requirement["title"],
        "text": requirement["text"],
        "mandatory": "true",
        "due_stage": requirement["due_stage"],
        "decision": "approved",
        "classification": "Not Applicable",
        "priority": "High",
    }
    endpoint = f"/api/requirements/{requirement['_id']}/review"
    assert client.post(endpoint, json=review, headers=headers).status_code == 422
    assert (
        client.post(endpoint, json={**review, "mandatory": "false"}, headers=headers).status_code
        == 204
    )
    assert requirement["requirement_id"] not in {r["requirement_id"] for r in matrix(db, "role")}
    assert (
        client.post(
            endpoint, json={**review, "classification": "Must Complete"}, headers=headers
        ).status_code
        == 204
    )

    document_id = requirement["document_id"]
    quote = "Complete workstation security training before accessing the support system."
    db.source_sections.insert_one(
        {
            "_id": "dependency-section",
            "document_id": document_id,
            "section_id": "dependency",
            "text": quote,
        }
    )

    def provider(settings, schema, template, payload, on_attempt):
        return Extraction(
            requirements=[
                {
                    "section_id": "dependency",
                    "title": "Support access",
                    "source_quote": quote,
                    "mandatory": True,
                    "due_stage": "Week 2",
                    "competency": "Support access",
                    "classification": "Must Complete",
                    "priority": "High",
                    "prerequisite_section_ids": [requirement["section_id"], "invented-section"],
                    "prerequisite_evidence": quote,
                }
            ]
        ), {"model": "TEST_DOUBLE"}

    job = enqueue(db, "admin", "extract", document_id)
    assert process_one(db, settings, provider)
    assert db.jobs.find_one({"_id": job["_id"]})["status"] == "completed"
    candidate = db.requirements.find_one({"section_id": "dependency"})
    assert candidate["prerequisites"] == []
    assert candidate["suggested_prerequisite_sections"] == [requirement["section_id"]]
    response = client.get(f"/api/requirements/{candidate['_id']}").json()
    assert response["suggestions"][0]["_id"] == requirement["_id"]
