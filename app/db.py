from datetime import datetime, timezone
from uuid import uuid4
from pymongo import MongoClient, ASCENDING


def now():
    return datetime.now(timezone.utc)


def uid():
    return uuid4().hex


def connect(settings):
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3500, tz_aware=True)
    client.admin.command("ping")
    return client, client[settings.mongodb_db_name]


def initialize(db):
    definitions = {
        "users": ("email", "password_hash", "role"),
        "sessions": ("token_hash", "user_id", "csrf"),
        "job_roles": ("name", "department"),
        "employees": ("name", "role_id", "department"),
        "documents": ("document_id", "version", "title", "status", "digest"),
        "source_sections": ("document_id", "section_id", "text"),
        "requirements": ("document_id", "section_id", "text", "status"),
        "jobs": ("kind", "status", "actor_id"),
        "plans": ("employee_id", "status"),
        "audit_events": ("actor_id", "action", "target_id"),
        "plan_reviews": ("plan_id", "actor_id", "decision", "comment"),
        "learning_progress": ("plan_id", "employee_id", "requirement_id"),
        "quiz_attempts": ("plan_id", "employee_id", "requirement_id"),
        "practical_submissions": ("plan_id", "employee_id", "requirement_id", "status"),
        "conflict_resolutions": ("role_id", "winner_id", "reason", "actor_id"),
        "consistency_experiments": ("employee_id", "actor_id", "snapshot_digest"),
    }
    existing = set(db.list_collection_names())
    for collection, fields in definitions.items():
        schema = {
            "bsonType": "object",
            "required": list(fields),
            "properties": {x: {"bsonType": "string"} for x in fields},
        }
        validator = {"$jsonSchema": schema}
        if collection not in existing:
            db.create_collection(collection, validator=validator)
        else:
            db.command("collMod", collection, validator=validator)
    db.users.create_index("email", unique=True)
    db.sessions.create_index("token_hash", unique=True)
    db.sessions.create_index("expires_at", expireAfterSeconds=0)
    db.login_limits.create_index("expires_at", expireAfterSeconds=0)
    db.job_roles.create_index("name", unique=True)
    db.documents.create_index([("document_id", ASCENDING), ("version", ASCENDING)], unique=True)
    db.documents.create_index("digest", unique=True)
    db.documents.create_index(
        "document_id",
        unique=True,
        partialFilterExpression={"status": "active"},
        name="one_active_version",
    )
    db.source_sections.create_index([("document_id", 1), ("section_id", 1)], unique=True)
    db.requirements.create_index(
        [("document_id", 1), ("section_id", 1), ("requirement_id", 1)], unique=True
    )
    db.requirements.create_index([("role_ids", 1), ("status", 1)])
    db.employees.create_index("manager_id")
    db.employees.create_index(
        "user_id",
        unique=True,
        partialFilterExpression={"user_id": {"$gt": ""}},
        name="one_employee_per_login",
    )
    db.plan_reviews.create_index([("plan_id", 1), ("created_at", 1)])
    db.conflict_resolutions.create_index("role_id")
    db.consistency_experiments.create_index([("employee_id", 1), ("created_at", -1)])
    db.learning_progress.create_index(
        [("plan_id", 1), ("employee_id", 1), ("requirement_id", 1)], unique=True
    )
    for collection in (db.quiz_attempts, db.practical_submissions):
        collection.create_index(
            [("plan_id", 1), ("employee_id", 1), ("requirement_id", 1), ("created_at", -1)]
        )
    db.practical_submissions.create_index(
        [("plan_id", 1), ("employee_id", 1), ("requirement_id", 1)],
        unique=True,
        partialFilterExpression={"status": "pending"},
        name="one_pending_submission",
    )
    db.jobs.create_index([("status", 1), ("lease_until", 1)])
    db.plans.create_index([("employee_id", 1), ("created_at", -1)])
    db.audit_events.create_index([("target_id", 1), ("created_at", -1)])


def audit(db, actor, action, target, details=None):
    db.audit_events.insert_one(
        {
            "_id": uid(),
            "actor_id": actor,
            "action": action,
            "target_id": target,
            "details": details or {},
            "created_at": now(),
        }
    )
