"""Local capacity/read latency sample; not a production uptime guarantee."""

import sys, time, json, statistics, platform, io
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.config import Settings, ROOT
from app.main import create_app
from app.db import now
from app.security import hash_password
from app.ingestion import parse
from app.schemas import FullOnboardingPlan
from app.validation import validate_plan
from app.policy import fingerprint
from tests.test_phase2 import full_item
from tests.conftest import csrf


def main():
    settings = Settings(
        _env_file=None,
        app_secret_key="b" * 48,
        mongodb_db_name="skillsprint_phase4_capacity_" + uuid4().hex,
        run_worker=False,
        upload_dir=ROOT / "tmp" / "capacity",
    )
    out = ROOT / "reports" / "phase4"
    out.mkdir(exist_ok=True)
    report = {
        "time": now().isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "fixture": "1000 employees, 100 roles, 1000 documents with source sections and approved requirements, 1000 one-module plans. Synthetic load, not AI evidence.",
        "requests": {},
    }
    with TestClient(create_app(settings)) as client:
        db = client.app.state.db
        try:
            db.users.insert_one(
                {
                    "_id": "admin",
                    "email": "capacity@test.local",
                    "password_hash": hash_password("Capacity-Test!2026"),
                    "name": "Capacity test",
                    "role": "admin",
                    "active": True,
                    "created_at": now(),
                }
            )
            db.job_roles.insert_many(
                [
                    {"_id": str(i), "name": "Role " + str(i), "department": "Evaluation"}
                    for i in range(100)
                ]
            )
            docs = []
            sections = []
            reqs = []
            emps = []
            plans = []
            for i in range(1000):
                key = str(i)
                rid = str(i % 100)
                text = "Employees must lock their workstation before leaving it unattended."
                doc = {
                    "_id": key,
                    "document_id": "CAP-" + key,
                    "version": "1",
                    "title": "Synthetic capacity policy " + key,
                    "status": "active",
                    "digest": key,
                    "filename": "capacity.pdf",
                    "category": "Policy",
                    "suspicious": False,
                    "created_at": now(),
                    "effective_date": "2026-01-01",
                }
                req = {
                    "_id": key,
                    "requirement_id": "CAP-R" + key,
                    "document_id": key,
                    "section_id": "s1",
                    "text": text,
                    "status": "approved",
                    "mandatory": True,
                    "role_ids": [rid],
                    "due_stage": "Week 1",
                    "prerequisites": [],
                    "title": "Lock screen",
                }
                section = {"_id": key, "document_id": key, "section_id": "s1", "text": text}
                employee = {
                    "_id": key,
                    "name": "Capacity learner " + key,
                    "role_id": rid,
                    "role_name": "Role " + rid,
                    "department": "Evaluation",
                    "experience": "Beginner",
                    "joining_date": "2026-09-25",
                    "manager_id": "admin",
                    "user_id": "",
                }
                item = full_item(
                    {
                        "requirement_id": req["requirement_id"],
                        "source_document_id": key,
                        "source_section_id": "s1",
                        "text": text,
                        "mandatory": True,
                    },
                    rid,
                )
                content = FullOnboardingPlan(
                    title="Synthetic load plan " + key,
                    summary="Not AI output",
                    role_id=rid,
                    items=[item],
                )
                plans.append(
                    {
                        "_id": key,
                        "employee_id": key,
                        "role_id": rid,
                        "status": "Review required",
                        "content": content.model_dump(),
                        "matrix_snapshot": [req],
                        "snapshot_digest": fingerprint([req]),
                        "source_document_ids": [key],
                        "validation": validate_plan(content, [req], [doc], [section], rid),
                        "created_at": now(),
                    }
                )
                docs.append(doc)
                sections.append(section)
                reqs.append(req)
                emps.append(employee)
            for name, values in [
                ("documents", docs),
                ("source_sections", sections),
                ("requirements", reqs),
                ("employees", emps),
                ("plans", plans),
            ]:
                db[name].insert_many(values)
            token = csrf(client.get("/login").text)
            assert (
                client.post(
                    "/login",
                    data={
                        "email": "capacity@test.local",
                        "password": "Capacity-Test!2026",
                        "csrf_token": token,
                    },
                ).status_code
                == 200
            )
            for route in [
                "/health",
                "/",
                "/employees",
                "/documents",
                "/plans",
                "/reports?role_id=0",
                "/reports.csv?role_id=0",
                "/reports",
            ]:
                times = []
                statuses = []
                for _ in range(3):
                    start = time.perf_counter()
                    response = client.get(route)
                    times.append(round((time.perf_counter() - start) * 1000, 2))
                    statuses.append(response.status_code)
                report["requests"][route] = {
                    "milliseconds": times,
                    "median_ms": statistics.median(times),
                    "max_ms": max(times),
                    "statuses": statuses,
                }
                print(route, report["requests"][route], flush=True)
            start = time.perf_counter()
            successes = 0
            for _ in range(30):
                successes += client.get("/health").status_code == 200
            report["availability_sample"] = {
                "successful": successes,
                "requests": 30,
                "duration_seconds": round(time.perf_counter() - start, 3),
                "limitation": "Short local request sample, not 99% availability evidence.",
            }
            pdf = ROOT / "sample_documents/asterbridge/current/POL-05_v2_0.pdf"
            start = time.perf_counter()
            blocks = parse(pdf.read_bytes(), pdf.name)
            report["pdf_ingestion"] = {
                "parse_ms": round((time.perf_counter() - start) * 1000, 2),
                "sections": len(blocks),
                "bytes": pdf.stat().st_size,
            }
            report["database_bytes"] = db.command("dbStats")["dataSize"]
        finally:
            (out / "capacity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            assert db.name.startswith("skillsprint_phase4_capacity_")
            db.client.drop_database(db.name)


if __name__ == "__main__":
    main()
