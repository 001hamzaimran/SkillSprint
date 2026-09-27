"""Reviewed rule metadata, explicit precedence and immutable matrix identities."""

import hashlib
import json
from collections import defaultdict
from .ingestion import normalized


def fingerprint(requirements):
    fields = []
    for req in requirements:
        value = {
            k: req.get(k)
            for k in (
                "_id",
                "requirement_id",
                "text",
                "mandatory",
                "due_stage",
                "priority",
                "classification",
                "status",
                "role_ids",
                "prerequisites",
                "document_id",
                "section_id",
            )
        }
        if req.get("policy_rule"):
            value["policy_rule"] = req["policy_rule"]
        fields.append(value)
    return hashlib.sha256(
        json.dumps(sorted(fields, key=lambda r: r["_id"]), sort_keys=True).encode()
    ).hexdigest()


def raw_matrix(db, role_id):
    candidates = list(
        db.requirements.find(
            {"status": "approved", "$or": [{"role_ids": role_id}, {"role_ids": {"$size": 0}}]}
        ).sort("requirement_id", 1)
    )
    ids = list({r["document_id"] for r in candidates})
    active = {
        d["_id"] for d in db.documents.find({"_id": {"$in": ids}, "status": "active"}, {"_id": 1})
    }
    return [
        r
        for r in candidates
        if r["document_id"] in active and r.get("classification") != "Not Applicable"
    ]


def conflict_groups(requirements, role_id):
    groups = defaultdict(list)
    for req in requirements:
        rule = req.get("policy_rule")
        if rule:
            groups[(rule["key"], normalized(rule["condition"]).casefold())].append(req)
    result = []
    for (key, condition), members in groups.items():
        values = {
            (
                normalized(r["policy_rule"]["value"]).casefold(),
                normalized(r["policy_rule"]["exception"]).casefold(),
            )
            for r in members
        }
        if len(values) > 1:
            identity = hashlib.sha256(
                (role_id + key + condition + fingerprint(members)).encode()
            ).hexdigest()
            result.append(
                {"_id": identity, "key": key, "condition": condition, "requirements": members}
            )
    return result


def matrix_state(db, role_id):
    raw = raw_matrix(db, role_id)
    groups = conflict_groups(raw, role_id)
    excluded = set()
    for group in groups:
        resolution = db.conflict_resolutions.find_one({"_id": group["_id"], "role_id": role_id})
        ids = {r["requirement_id"] for r in group["requirements"]}
        if resolution and resolution["winner_id"] in ids:
            excluded.update(ids - {resolution["winner_id"]})
            group["resolution"] = resolution
        else:
            group["resolution"] = None
    return {
        "raw": raw,
        "requirements": [r for r in raw if r["requirement_id"] not in excluded],
        "conflicts": groups,
        "unresolved": [g for g in groups if not g["resolution"]],
        "excluded": sorted(excluded),
    }


def matrix(db, role_id):
    return matrix_state(db, role_id)["requirements"]


def dependency_findings(requirements):
    graph = {r["requirement_id"]: r.get("prerequisites", []) for r in requirements}
    errors = []
    for key, deps in graph.items():
        for dep in deps:
            if dep not in graph:
                errors.append(
                    {
                        "code": "PREREQUISITE_UNAVAILABLE",
                        "requirement_id": key,
                        "message": f"Prerequisite {dep} is not in the effective role matrix.",
                    }
                )
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            return True
        if key in visited:
            return False
        visiting.add(key)
        cycle = any(visit(dep) for dep in graph.get(key, []) if dep in graph)
        visiting.remove(key)
        visited.add(key)
        return cycle

    if any(visit(key) for key in graph):
        errors.append(
            {
                "code": "PREREQUISITE_CYCLE",
                "message": "The role matrix has a prerequisite cycle. Correct it before publication.",
            }
        )
    return errors


def selective_delta(plan, requirements, employee_snapshot=None):
    old = {r["requirement_id"]: r for r in plan.get("matrix_snapshot", [])}
    new = {r["requirement_id"]: r for r in requirements}
    items = {i["requirement_id"]: i for i in plan["content"]["items"]}
    retained = {
        key
        for key in new
        if key in old
        and key in items
        and fingerprint([new[key]]) == fingerprint([old[key]])
        and "quiz" in items[key]
    }
    if (
        employee_snapshot
        and plan.get("employee_snapshot")
        and plan["employee_snapshot"] != employee_snapshot
    ):
        retained = set()
    # A prerequisite change invalidates dependent learning, even if its own text is unchanged.
    while True:
        keep = {
            key
            for key in retained
            if all(dep in retained for dep in new[key].get("prerequisites", []))
        }
        if keep == retained:
            break
        retained = keep
    return {
        "retained": sorted(retained),
        "regenerate": sorted(set(new) - retained),
        "removed": sorted(set(items) - set(new)),
        "changed": sorted((set(old) & set(new)) - retained),
        "added": sorted(set(new) - set(old)),
    }
