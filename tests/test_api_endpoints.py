from .test_phase2 import training


def test_spa_serving(workspace):
    client, _, _ = workspace
    res = client.get("/app")
    assert res.status_code == 200
    assert "SkillSprint AI" in res.text
    assert 'id="root"' in res.text

    res_deep = client.get("/app/documents/123")
    assert res_deep.status_code == 200
    assert 'id="root"' in res_deep.text


def test_api_auth_and_session(workspace):
    client, db, _ = workspace

    # Unauthenticated /api/auth/me should return 401 JSON
    res = client.get("/api/auth/me")
    assert res.status_code == 401
    assert res.headers.get("content-type", "").startswith("application/json")

    # Login via /api/auth/login
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "Test-password-123!"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == "admin@test.local"
    assert data["user"]["role"] == "admin"
    assert "csrf_token" in data

    # Verify session via /api/auth/me
    res = client.get("/api/auth/me")
    assert res.status_code == 200
    me = res.json()
    assert me["user"]["email"] == "admin@test.local"
    assert me["user"]["role"] == "admin"
    assert "csrf_token" in me
    assert "password_hash" not in me["user"]
    assert "password_hash" not in data["user"]

    # Dashboard endpoint
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    dash = res.json()
    assert "stats" in dash
    assert "plans" in dash
    assert "ai_ready" in dash

    # Roles API
    res = client.get("/api/roles")
    assert res.status_code == 200
    roles = res.json()["roles"]
    assert isinstance(roles, list)

    # Create a role with CSRF
    res = client.post(
        "/api/roles",
        json={"name": "Frontend Dev", "department": "Engineering", "description": "Builds UI"},
        headers={"X-CSRF-Token": data["csrf_token"]},
    )
    assert res.status_code == 201
    assert "role" in res.json()

    # Logout
    res = client.post(
        "/api/auth/logout",
        headers={"X-CSRF-Token": data["csrf_token"]},
    )
    assert res.status_code == 204

    # /api/auth/me should now be 401
    assert client.get("/api/auth/me").status_code == 401


def test_api_documents_and_employees(workspace):
    client, db, _ = workspace

    # Login as admin
    res = client.post(
        "/api/auth/login",
        json={"email": "admin@test.local", "password": "Test-password-123!"},
    )
    csrf_tok = res.json()["csrf_token"]

    # Documents API
    res = client.get("/api/documents")
    assert res.status_code == 200
    doc_data = res.json()
    assert "documents" in doc_data
    assert "roles" in doc_data

    # Employees API
    res = client.get("/api/employees")
    assert res.status_code == 200
    emp_data = res.json()
    assert "employees" in emp_data
    assert "roles" in emp_data

    # Create a role first
    res = client.post(
        "/api/roles",
        json={"name": "Developer", "department": "Engineering", "description": "Software dev"},
        headers={"X-CSRF-Token": csrf_tok},
    )
    assert res.status_code == 201
    role_id = res.json()["role"]["_id"]

    # Add Employee API
    res = client.post(
        "/api/employees",
        json={
            "name": "Jane Doe",
            "role_id": role_id,
            "experience": "Intermediate",
            "joining_date": "2026-01-15",
        },
        headers={"X-CSRF-Token": csrf_tok},
    )
    assert res.status_code == 201
    created_emp = res.json()["employee"]
    assert created_emp["name"] == "Jane Doe"

    # Verification API
    res = client.get(f"/api/verification?role_id={role_id}")
    assert res.status_code == 200
    ver = res.json()
    assert "state" in ver
    assert "roles" in ver
    assert "dependencies" in ver


def test_react_publication_learning_and_reporting(training):
    client, db, _, plan, _ = training
    plan_id = plan["_id"]
    admin = client.post("/api/auth/login", json={
        "email": "admin@test.local", "password": "Test-password-123!",
    }).json()
    headers = {"X-CSRF-Token": admin["csrf_token"]}
    path = f"/api/plans/{plan_id}/review"
    review = {"decision": "approve", "comment": "Reviewed lessons and source evidence."}
    assert client.post(path, json=review).status_code == 403
    assert client.post(path, json=review, headers=headers).status_code == 422
    review["confirmed"] = "true"
    assert client.post(path, json=review, headers=headers).status_code == 204
    assert db.employees.find_one({"_id": "learner"})["active_plan_id"] == plan_id

    dashboard = client.get("/api/dashboard").json()
    assert dashboard["stats"]["employees"] == 1
    assert dashboard["plans"][0]["content"]["title"] == plan["content"]["title"]
    matrix = client.get("/api/matrix?role_id=role").json()
    assert matrix["requirements"][0]["document_id"]
    reports = client.get("/api/reports?status=Published").json()
    assert reports["rows"][0]["assigned"] is True
    assert reports["rows"][0]["plan"]["validation"]["coverage"] == 100

    learner = client.post("/api/auth/login", json={
        "email": "employee@test.local", "password": "Test-password-123!",
    }).json()
    headers = {"X-CSRF-Token": learner["csrf_token"]}
    workspace = client.get(f"/api/learning/{plan_id}").json()
    assert workspace["active"] is True
    assert "correct_index" not in workspace["report"]["rows"][0]["item"]["quiz"]
    item = plan["content"]["items"][0]
    item_path = f"/api/learning/{plan_id}/{item['requirement_id']}"
    assert client.post(item_path + "/progress", headers=headers, json={
        "lesson_read": True, "checked": [0, 1],
    }).status_code == 204
    assert client.post(item_path + "/quiz", headers=headers, json={"answer": 0}).json()["passed"]
    assert client.get("/api/users").status_code == 403
