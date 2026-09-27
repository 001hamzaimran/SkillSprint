"""Reproducible set comparisons, not an AI judge of its own output."""

from .ingestion import normalized


def compare_plans(left, right):
    def sets(plan):
        requirements = {r["requirement_id"]: r for r in plan.get("matrix_snapshot", [])}
        items = plan["content"]["items"]
        return {
            "requirements": {i["requirement_id"] for i in items},
            "sources": {
                (i["requirement_id"], i["source_document_id"], i["source_section_id"])
                for i in items
            },
            "module_categories": {
                (
                    i["requirement_id"],
                    normalized(
                        (i.get("policy_facts") or {}).get("module_category")
                        or requirements.get(i["requirement_id"], {}).get("competency")
                        or i["module_title"]
                    ).casefold(),
                )
                for i in items
            },
            "assessment_topics": {
                (
                    i["requirement_id"],
                    normalized(
                        (i.get("policy_facts") or {}).get("assessment_topic")
                        or i.get("quiz", {}).get("question", "")
                    ).casefold(),
                )
                for i in items
                if i.get("quiz")
            },
        }

    a, b = sets(left), sets(right)
    categories = []
    for key in a:
        union = a[key] | b[key]
        categories.append(
            {
                "category": key,
                "intersection": len(a[key] & b[key]),
                "union": len(union),
                "score": round(100 * len(a[key] & b[key]) / len(union), 1) if union else None,
            }
        )
    comparable = (
        left.get("snapshot_digest") == right.get("snapshot_digest")
        and bool(left.get("employee_snapshot"))
        and left.get("employee_snapshot") == right.get("employee_snapshot")
        and left.get("model") == right.get("model")
        and left.get("prompt_version") == right.get("prompt_version")
        and left.get("generation", {}).get("prompt_sha256")
        == right.get("generation", {}).get("prompt_sha256")
        and left.get("stage_days") == right.get("stage_days")
        and left.get("origin", "ai_generation") == "ai_generation"
        and right.get("origin", "ai_generation") == "ai_generation"
    )
    scores = [x["score"] for x in categories if x["score"] is not None]
    left_items = {i["requirement_id"]: i for i in left["content"]["items"]}
    right_items = {i["requirement_id"]: i for i in right["content"]["items"]}
    rows = []
    for key in sorted(set(left_items) | set(right_items)):
        before, after = left_items.get(key), right_items.get(key)
        rows.append(
            {
                "requirement_id": key,
                "before": before,
                "after": after,
                "status": (
                    "Added"
                    if not before
                    else "Removed" if not after else "Unchanged" if before == after else "Changed"
                ),
            }
        )
    return {
        "comparable": comparable,
        "categories": categories,
        "consistency_score": round(sum(scores) / len(scores), 1) if comparable and scores else None,
        "rows": rows,
        "method": "Jaccard overlap: intersection / union for requirement IDs, versioned sources, module categories and assessment topics; aggregate is the mean of non-empty categories.",
        "limitation": "A consistency score measures repeatability, not factual correctness. Unannotated category/topic labels use competency/title/question text and are sensitive to wording.",
    }
