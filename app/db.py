"""PostgreSQL-backed document repository used by the application.

The public collection API intentionally mirrors the small PyMongo subset used by
SkillSprint. Business modules therefore stay focused on authorization, learning,
and validation while PostgreSQL provides durable JSONB storage and transactions.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from uuid import uuid4

import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb


class DuplicateKeyError(Exception):
    pass


class ReturnDocument:
    BEFORE = False
    AFTER = True


def now():
    return datetime.now(timezone.utc)


def uid():
    return uuid4().hex


def _json_default(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    raise TypeError(f"Unsupported PostgreSQL JSON value: {type(value).__name__}")


def _restore(value):
    if isinstance(value, list):
        return [_restore(item) for item in value]
    if isinstance(value, dict):
        return {key: _restore(item) for key, item in value.items()}
    if (
        isinstance(value, str)
        and "T" in value
        and (value.endswith("Z") or re.search(r"[+-]\d\d:\d\d$", value))
    ):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return value


def _get(document, dotted, missing=None):
    value = document
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            return missing
        value = value[part]
    return value


def _set(document, dotted, value):
    target = document
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = deepcopy(value)


def _unset(document, dotted):
    target = document
    parts = dotted.split(".")
    for part in parts[:-1]:
        if not isinstance(target, dict) or part not in target:
            return
        target = target[part]
    if isinstance(target, dict):
        target.pop(parts[-1], None)


_MISSING = object()


def _condition(actual, expected):
    if not isinstance(expected, dict) or not any(str(key).startswith("$") for key in expected):
        return (
            expected in actual
            if isinstance(actual, list) and not isinstance(expected, list)
            else actual == expected
        )
    for operator, wanted in expected.items():
        if operator == "$in":
            ok = bool(set(actual) & set(wanted)) if isinstance(actual, list) else actual in wanted
        elif operator == "$ne":
            ok = actual != wanted
        elif operator == "$gt":
            ok = actual is not _MISSING and actual > wanted
        elif operator == "$gte":
            ok = actual is not _MISSING and actual >= wanted
        elif operator == "$lt":
            ok = actual is not _MISSING and actual < wanted
        elif operator == "$lte":
            ok = actual is not _MISSING and actual <= wanted
        elif operator == "$exists":
            ok = (actual is not _MISSING) == bool(wanted)
        elif operator == "$size":
            ok = isinstance(actual, list) and len(actual) == wanted
        elif operator == "$regex":
            flags = re.I if "i" in str(expected.get("$options", "")) else 0
            ok = actual is not _MISSING and re.search(wanted, str(actual), flags) is not None
        elif operator == "$options":
            continue
        else:
            raise ValueError(f"Unsupported query operator: {operator}")
        if not ok:
            return False
    return True


def _matches(document, query):
    query = query or {}
    for key, expected in query.items():
        if key == "$or":
            if not any(_matches(document, option) for option in expected):
                return False
            continue
        if not _condition(_get(document, key, _MISSING), expected):
            return False
    return True


def _project(document, projection):
    if not projection:
        return deepcopy(document)
    included = [key for key, value in projection.items() if value]
    if included:
        result = {}
        for key in included:
            value = _get(document, key, _MISSING)
            if value is not _MISSING:
                _set(result, key, value)
        if projection.get("_id", 1) and "_id" in document:
            result.setdefault("_id", document["_id"])
        return result
    result = deepcopy(document)
    for key, value in projection.items():
        if not value:
            _unset(result, key)
    return result


def _apply_update(document, update, inserting=False):
    result = deepcopy(document)
    for operator, values in update.items():
        if operator == "$set":
            for key, value in values.items():
                _set(result, key, value)
        elif operator == "$setOnInsert":
            if inserting:
                for key, value in values.items():
                    _set(result, key, value)
        elif operator == "$inc":
            for key, value in values.items():
                _set(result, key, (_get(result, key, 0) or 0) + value)
        elif operator == "$push":
            for key, value in values.items():
                items = list(_get(result, key, []) or [])
                items.append(deepcopy(value))
                _set(result, key, items)
        elif operator == "$unset":
            for key in values:
                _unset(result, key)
        else:
            raise ValueError(f"Unsupported update operator: {operator}")
    return result


@dataclass
class WriteResult:
    matched_count: int = 0
    modified_count: int = 0
    inserted_id: str | None = None
    upserted_id: str | None = None


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, key, direction=1):
        if isinstance(key, list):
            keys = key
        else:
            keys = [(key, direction)]
        for field, order in reversed(keys):
            self.rows.sort(
                key=lambda row: (_get(row, field, None) is None, _get(row, field, None)),
                reverse=order < 0,
            )
        return self

    def limit(self, count):
        self.rows = self.rows[:count]
        return self

    def __iter__(self):
        return iter(self.rows)


UNIQUE_RULES = {
    "users": [("email",)],
    "sessions": [("token_hash",)],
    "password_resets": [("token_hash",)],
    "job_roles": [("name",)],
    "documents": [("document_id", "version"), ("digest",)],
    "source_sections": [("document_id", "section_id")],
    "requirements": [("document_id", "section_id", "requirement_id")],
    "learning_progress": [("plan_id", "employee_id", "requirement_id")],
}


class Collection:
    def __init__(self, database, name):
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
            raise ValueError("Invalid collection name")
        self.database = database
        self.name = name

    def _table(self):
        return sql.Identifier(self.database.name, self.name)

    def _all(self, connection=None, lock=False):
        owns = connection is None
        connection = connection or self.database.connection()
        try:
            if lock:
                connection.execute(
                    sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(self._table())
                )
            rows = connection.execute(
                sql.SQL("SELECT data FROM {}").format(self._table())
            ).fetchall()
            return [_restore(row[0]) for row in rows]
        finally:
            if owns:
                connection.close()

    def _validate_unique(self, document, connection, replacing_id=None):
        rows = self._all(connection)
        rules = list(UNIQUE_RULES.get(self.name, []))
        if self.name == "employees" and document.get("user_id"):
            rules.append(("user_id",))
        if self.name == "documents" and document.get("status") == "active":
            rules.append(("document_id", "status"))
        if self.name == "practical_submissions" and document.get("status") == "pending":
            rules.append(("plan_id", "employee_id", "requirement_id", "status"))
        for fields in rules:
            values = tuple(_get(document, field, _MISSING) for field in fields)
            if _MISSING in values:
                continue
            for row in rows:
                if (
                    row.get("_id") != replacing_id
                    and tuple(_get(row, field, _MISSING) for field in fields) == values
                ):
                    raise DuplicateKeyError(f"Duplicate {self.name} key: {', '.join(fields)}")

    def create_index(self, *args, **kwargs):
        return kwargs.get("name", "postgres_jsonb_index")

    def insert_one(self, document):
        record = deepcopy(document)
        record.setdefault("_id", uid())
        with self.database.connection() as connection:
            connection.execute(
                sql.SQL("LOCK TABLE {} IN SHARE ROW EXCLUSIVE MODE").format(self._table())
            )
            self._insert_locked(connection, record)
        return WriteResult(inserted_id=str(record["_id"]))

    def _insert_locked(self, connection, record):
        self._validate_unique(record, connection)
        try:
            connection.execute(
                sql.SQL("INSERT INTO {} (id, data) VALUES (%s, %s)").format(self._table()),
                (
                    str(record["_id"]),
                    Jsonb(record, dumps=lambda value: json.dumps(value, default=_json_default)),
                ),
            )
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicateKeyError(str(exc)) from None

    def insert_many(self, documents):
        ids = [self.insert_one(document).inserted_id for document in documents]
        return type("InsertManyResult", (), {"inserted_ids": ids})()

    def find(self, query=None, projection=None):
        return Cursor(
            [_project(row, projection) for row in self._all() if _matches(row, query or {})]
        )

    def find_one(self, query=None, projection=None):
        return next(iter(self.find(query, projection).limit(1)), None)

    def count_documents(self, query):
        return sum(1 for row in self._all() if _matches(row, query or {}))

    def _replace_locked(self, connection, record):
        self._validate_unique(record, connection, replacing_id=str(record["_id"]))
        connection.execute(
            sql.SQL("UPDATE {} SET data=%s WHERE id=%s").format(self._table()),
            (
                Jsonb(record, dumps=lambda value: json.dumps(value, default=_json_default)),
                str(record["_id"]),
            ),
        )

    def update_one(self, query, update, upsert=False):
        with self.database.connection() as connection:
            rows = self._all(connection, lock=True)
            current = next((row for row in rows if _matches(row, query)), None)
            if current:
                changed = _apply_update(current, update)
                self._replace_locked(connection, changed)
                return WriteResult(matched_count=1, modified_count=int(changed != current))
            if upsert:
                base = {
                    key: value
                    for key, value in query.items()
                    if not key.startswith("$") and not isinstance(value, dict)
                }
                record = _apply_update(base, update, inserting=True)
                record.setdefault("_id", uid())
                self._insert_locked(connection, record)
                return WriteResult(upserted_id=str(record["_id"]))
            return WriteResult()

    def update_many(self, query, update):
        matched = modified = 0
        with self.database.connection() as connection:
            for current in self._all(connection, lock=True):
                if _matches(current, query):
                    matched += 1
                    changed = _apply_update(current, update)
                    modified += int(changed != current)
                    self._replace_locked(connection, changed)
        return WriteResult(matched_count=matched, modified_count=modified)

    def replace_one(self, query, replacement, upsert=False):
        with self.database.connection() as connection:
            rows = self._all(connection, lock=True)
            current = next((row for row in rows if _matches(row, query)), None)
            if current:
                record = deepcopy(replacement)
                record.setdefault("_id", current["_id"])
                self._replace_locked(connection, record)
                return WriteResult(matched_count=1, modified_count=int(record != current))
            if upsert:
                record = deepcopy(replacement)
                for key, value in query.items():
                    if not key.startswith("$") and not isinstance(value, dict):
                        record.setdefault(key, value)
                record.setdefault("_id", uid())
                self._insert_locked(connection, record)
                return WriteResult(upserted_id=str(record["_id"]))
            return WriteResult()

    def delete_one(self, query):
        with self.database.connection() as connection:
            rows = self._all(connection, lock=True)
            current = next((row for row in rows if _matches(row, query)), None)
            if current:
                connection.execute(
                    sql.SQL("DELETE FROM {} WHERE id=%s").format(self._table()),
                    (str(current["_id"]),),
                )
                return WriteResult(matched_count=1, modified_count=1)
        return WriteResult()

    def delete_many(self, query):
        ids = [str(row["_id"]) for row in self._all() if _matches(row, query)]
        if ids:
            with self.database.connection() as connection:
                connection.execute(
                    sql.SQL("DELETE FROM {} WHERE id = ANY(%s)").format(self._table()), (ids,)
                )
        return WriteResult(matched_count=len(ids), modified_count=len(ids))

    def find_one_and_delete(self, query):
        with self.database.connection() as connection:
            rows = self._all(connection, lock=True)
            current = next((row for row in rows if _matches(row, query)), None)
            if current:
                connection.execute(
                    sql.SQL("DELETE FROM {} WHERE id=%s").format(self._table()),
                    (str(current["_id"]),),
                )
            return current

    def find_one_and_update(self, query, update, sort=None, return_document=False):
        with self.database.connection() as connection:
            rows = [row for row in self._all(connection, lock=True) if _matches(row, query)]
            if sort:
                rows = list(Cursor(rows).sort(sort))
            if not rows:
                return None
            current = rows[0]
            changed = _apply_update(current, update)
            self._replace_locked(connection, changed)
            return changed if return_document else current


COLLECTIONS = (
    "users",
    "sessions",
    "password_resets",
    "login_limits",
    "job_roles",
    "employees",
    "documents",
    "source_sections",
    "requirements",
    "jobs",
    "plans",
    "audit_events",
    "plan_reviews",
    "learning_progress",
    "quiz_attempts",
    "practical_submissions",
    "conflict_resolutions",
    "consistency_experiments",
)


class Database:
    def __init__(self, database_url, name, client):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name):
            raise ValueError("POSTGRES_SCHEMA must use lowercase letters, numbers, and underscores")
        self.database_url = database_url
        self.name = name
        self.client = client

    def connection(self):
        return psycopg.connect(self.database_url, connect_timeout=5)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return Collection(self, name)

    def __getitem__(self, name):
        return Collection(self, name)

    def command(self, name, *args, **kwargs):
        if name == "ping":
            with self.connection() as connection:
                connection.execute("SELECT 1")
            return {"ok": 1}
        if name == "dbStats":
            with self.connection() as connection:
                size = connection.execute(
                    "SELECT COALESCE(SUM(pg_total_relation_size(c.oid)),0) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s",
                    (self.name,),
                ).fetchone()[0]
            return {"dataSize": size}
        raise ValueError(f"Unsupported PostgreSQL command: {name}")


class Client:
    def __init__(self, database_url):
        self.database_url = database_url

    def close(self):
        pass

    def drop_database(self, name):
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", name):
            raise ValueError("Invalid PostgreSQL schema")
        with psycopg.connect(self.database_url, connect_timeout=5) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(name))
            )


def connect(settings):
    client = Client(settings.database_url)
    db = Database(settings.database_url, settings.postgres_schema, client)
    db.command("ping")
    return client, db


def initialize(db):
    with db.connection() as connection:
        connection.execute(
            sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(db.name))
        )
        for name in COLLECTIONS:
            connection.execute(
                sql.SQL(
                    "CREATE TABLE IF NOT EXISTS {} (id text PRIMARY KEY, data jsonb NOT NULL)"
                ).format(sql.Identifier(db.name, name))
            )
            connection.execute(
                sql.SQL("CREATE INDEX IF NOT EXISTS {} ON {} USING gin (data)").format(
                    sql.Identifier(f"{name}_data_gin"), sql.Identifier(db.name, name)
                )
            )


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
