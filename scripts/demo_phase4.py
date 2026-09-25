"""Local presentation workspace. Replays saved real API output; never fresh generation.
Synthetic reviewer decisions and learner history are explicitly labeled.
"""

import sys, json
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
from docx import Document
from app.config import Settings, ROOT
from app.db import connect, initialize, now
from app.main import create_app
from app.security import hash_password
from app.policy import fingerprint
from app.learning import learning_checks


def main():
    settings = Settings().model_copy(
        update={
            "mongodb_db_name": "skillsprint_phase4_demo_" + uuid4().hex,
            "run_worker": False,
            "upload_dir": ROOT / "tmp" / "phase4_demo",
            "port": 8001,
        }
    )
    client, db = connect(settings)
    initialize(db)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    evidence = json.loads((ROOT / "reports/phase3_live_smoke.json").read_text(encoding="utf-8"))
    try:
        db.users.insert_one(
            {
                "_id": "admin",
                "email": "admin@demo.local",
                "name": "Demo reviewer (synthetic)",
                "role": "admin",
                "password_hash": hash_password("Demo-Phase4!2026"),
                "active": True,
                "created_at": now(),
            }
        )
        db.job_roles.insert_one(
            {"_id": "support", "name": "Fictional Support", "department": "Support"}
        )
        db.employees.insert_one(
            {
                "_id": "learner",
                "name": "Fictional demonstration learner",
                "role_id": "support",
                "role_name": "Fictional Support",
                "department": "Support",
                "experience": "Beginner",
                "joining_date": "2026-09-25",
                "manager_id": "admin",
                "user_id": "",
                "active_plan_id": "demo-base",
            }
        )
        for label, part in [("base", evidence["initial"]), ("update", evidence["selective"])]:
            reqs = []
            for item in part["content"]["items"]:
                did = item["source_document_id"]
                sid = item["source_section_id"]
                rid = item["requirement_id"]
                identifier = "LOCK-01" if "lock" in item["source_quote"].lower() else "ACK-01"
                version = "2" if "1 working hour" in item["source_quote"] else "1"
                file = settings.upload_dir / (did + ".docx")
                doc = Document()
                doc.add_paragraph(item["source_quote"])
                doc.save(file)
                db.documents.update_one(
                    {"_id": did},
                    {
                        "$setOnInsert": {
                            "document_id": identifier,
                            "version": version,
                            "title": "Fictional " + identifier,
                            "status": "active",
                            "digest": did,
                            "filename": file.name,
                            "path": str(file),
                            "effective_date": "2026-01-01" if version == "1" else "2026-02-01",
                            "category": "Policy",
                            "role_ids": ["support"],
                            "suspicious": False,
                            "created_at": now(),
                        }
                    },
                    upsert=True,
                )
                db.source_sections.update_one(
                    {"document_id": did, "section_id": sid},
                    {
                        "$setOnInsert": {
                            "_id": did + sid,
                            "text": item["source_quote"],
                            "heading": identifier,
                            "location": "Replayed original API evidence",
                            "page": None,
                            "suspicious": False,
                        }
                    },
                    upsert=True,
                )
                req = {
                    "_id": rid,
                    "requirement_id": rid,
                    "document_id": did,
                    "section_id": sid,
                    "text": item["source_quote"],
                    "title": identifier,
                    "mandatory": True,
                    "status": "approved",
                    "role_ids": ["support"],
                    "due_stage": "Week 1",
                    "prerequisites": [],
                    "policy_rule": item.get("policy_facts"),
                }
                db.requirements.replace_one({"_id": rid}, req, upsert=True)
                reqs.append(req)
            plan = {
                "_id": "demo-" + label,
                "employee_id": "learner",
                "role_id": "support",
                "status": "Published" if label == "base" else "Review required",
                "content": part["content"],
                "validation": part["validation"],
                "learning_checks": learning_checks(part["content"]),
                "source_document_ids": list({r["document_id"] for r in reqs}),
                "matrix_snapshot": reqs,
                "snapshot_digest": fingerprint(reqs),
                "created_at": now(),
                "created_by": "admin",
                "generation": part["generation"],
                "prompt_version": "generate_v3",
                "model": evidence["model"],
                "origin": "ai_generation" if label == "base" else "selective_update",
                "parent_plan_id": "demo-base" if label == "update" else None,
                "update_delta": part.get("delta"),
                "replay_note": "Saved real API result; synthetic local presentation state.",
            }
            if label == "base":
                plan["published_at"] = now()
                db.documents.update_many(
                    {"document_id": "ACK-01"}, {"$set": {"status": "superseded"}}
                )
            db.plans.insert_one(plan)
        db.plans.update_one({"_id": "demo-base"}, {"$set": {"status": "Stale sources"}})
        print("DEMO ONLY http://localhost:8001 ; admin@demo.local / Demo-Phase4!2026", flush=True)
        uvicorn.run(create_app(settings), host="127.0.0.1", port=8001)
    finally:
        assert db.name.startswith("skillsprint_phase4_demo_")
        client.drop_database(db.name)
        client.close()


if __name__ == "__main__":
    main()
