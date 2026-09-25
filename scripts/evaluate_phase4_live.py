"""Billable real generation for all ten complete 88-requirement role matrices.
Uses an isolated disposable database. Fixture approvals are NOT human review.
Outputs are saved as each role completes, including failures. No cached output
is passed off as a fresh request. Four independent leased workers are used only
for this evaluation; the normal local app still uses one worker.
"""

import sys, json, time, csv, hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import Settings, ROOT
from app.db import connect, initialize, now
from app.ingestion import ingest, normalized
from app.worker import enqueue, process_one
from app.generation import structured

OUT = ROOT / "reports" / "phase4"
OUT.mkdir(parents=True, exist_ok=True)


def save(path, value):
    path.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")


def main():
    settings = Settings().model_copy(
        update={
            "mongodb_db_name": "skillsprint_phase4_live_" + uuid4().hex,
            "run_worker": False,
            "upload_dir": ROOT / "tmp" / "phase4_live_uploads",
        }
    )
    client, db = connect(settings)
    initialize(db)
    pack = ROOT / "sample_documents" / "asterbridge"
    read = lambda name: json.loads(
        (pack / "reference" / f"{name}.json").read_text(encoding="utf-8")
    )
    report = {
        "started_at": now(),
        "model": settings.genai_model,
        "workers": 4,
        "scope": "10 full role matrices, 88 requirements each",
        "approval_note": "Explicit automated fixture approval; human review pending",
        "roles": [],
    }
    started = time.perf_counter()
    try:
        refs = read("requirements")
        roledefs = read("roles")
        mapping = {}
        for d in read("document_register"):
            if d["status"] != "approved":
                continue
            path = pack / d["source_path"]
            doc = ingest(
                db,
                settings,
                path.read_bytes(),
                path.name,
                {
                    "document_id": d["document_id"],
                    "version": d["version"],
                    "title": d["title"],
                    "effective_date": d["effective_from"],
                    "category": d["category"],
                    "role_ids": d["role_ids"] if len(d["role_ids"]) == 1 else [],
                },
                "evaluation",
            )
            db.documents.update_one({"_id": doc["_id"]}, {"$set": {"status": "active"}})
            for r in db.requirements.find({"document_id": doc["_id"]}):
                ref = next(
                    x
                    for x in refs
                    if x["source_document_id"] == d["document_id"]
                    and normalized(x["source_quote"]) == r["text"]
                )
                mapping[ref["requirement_id"]] = r["requirement_id"]
                db.requirements.update_one(
                    {"_id": r["_id"]},
                    {
                        "$set": {
                            "status": "approved",
                            "due_stage": ref["due_stage"],
                            "reference_fixture_id": ref["requirement_id"],
                        }
                    },
                )
        for ref in refs:
            db.requirements.update_one(
                {"reference_fixture_id": ref["requirement_id"]},
                {"$set": {"prerequisites": [mapping[x] for x in ref["prerequisites"]]}},
            )
        for role in roledefs:
            rid = role["role_id"]
            db.job_roles.insert_one(
                {"_id": rid, "name": role["title"], "department": role["department"]}
            )
            db.employees.insert_one(
                {
                    "_id": rid,
                    "name": "Fictional evaluation " + rid,
                    "role_id": rid,
                    "role_name": role["title"],
                    "department": role["department"],
                    "experience": "Beginner",
                    "joining_date": "2026-09-25",
                }
            )
            enqueue(db, "evaluation", "generate", rid)

        def run():
            while True:
                requests = []
                t = time.perf_counter()

                def logged(settings, schema, template, payload, on_attempt):
                    record = {
                        "template": template,
                        "prompt_sha256": hashlib.sha256(
                            (ROOT / "prompt_templates" / template).read_bytes()
                        ).hexdigest(),
                        "payload": payload,
                    }
                    requests.append(record)
                    return structured(settings, schema, template, payload, on_attempt)

                if not process_one(db, settings, logged):
                    break
                # Each payload carries its role, providing an unambiguous per-worker result.
                if not requests:
                    continue
                rid = requests[0]["payload"]["employee"]["role_id"]
                job = db.jobs.find_one({"target_id": rid})
                plan = db.plans.find_one({"_id": job["_id"]})
                result = {
                    "role_id": rid,
                    "elapsed_seconds": round(time.perf_counter() - t, 3),
                    "job": job,
                    "plan": plan,
                    "requests": requests,
                }
                save(OUT / f"role_{rid}.json", result)
                print(
                    json.dumps(
                        {
                            "role": rid,
                            "status": job["status"],
                            "items": len(plan["content"]["items"]) if plan else 0,
                            "core_passed": plan["validation"]["core_passed"] if plan else False,
                            "seconds": result["elapsed_seconds"],
                        }
                    ),
                    flush=True,
                )

        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(run) for _ in range(4)]
            for f in futures:
                f.result()
        rows = []
        for role in roledefs:
            rid = role["role_id"]
            path = OUT / f"role_{rid}.json"
            if not path.exists():
                report["roles"].append(
                    {"role_id": rid, "status": "failed", "reason": "No provider request recorded"}
                )
                continue
            result = json.loads(path.read_text(encoding="utf-8"))
            plan = result["plan"]
            report["roles"].append(
                {
                    "role_id": rid,
                    "status": result["job"]["status"],
                    "elapsed_seconds": result["elapsed_seconds"],
                    "items": len(plan["content"]["items"]) if plan else 0,
                    "core_passed": plan["validation"]["core_passed"] if plan else False,
                }
            )
            if plan:
                for row in plan["validation"]["rows"]:
                    item = next(
                        i
                        for i in plan["content"]["items"]
                        if i["requirement_id"] == row["requirement_id"]
                    )
                    rows.append(
                        {
                            "role": rid,
                            **row,
                            "source": item["source_document_id"] + "/" + item["source_section_id"],
                            "coverage_status": (
                                "Covered" if row["result"] == "Match" else "Invalid item"
                            ),
                            "validation_status": plan["validation"]["status"],
                            "errors": ";".join(row["errors"]),
                        }
                    )
        if rows:
            with (OUT / "requirement_comparison.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
        report.update(
            elapsed_seconds=round(time.perf_counter() - started, 3),
            comparison_rows=len(rows),
            finished_at=now(),
        )
    finally:
        save(OUT / "live_evaluation.json", report)
        assert db.name.startswith("skillsprint_phase4_live_")
        client.drop_database(db.name)
        client.close()


if __name__ == "__main__":
    main()
