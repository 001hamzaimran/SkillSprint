"""Independent core validator. No model, SDK, network, or generated ground truth."""

from collections import Counter
from difflib import SequenceMatcher
import re
from .ingestion import normalized
from .schemas import STAGES
from .policy import conflict_groups, dependency_findings


def validate_plan(plan, requirements, documents, sections, role_id):
    expected = {
        r["requirement_id"]: r
        for r in requirements
        if r["status"] == "approved" and (not r["role_ids"] or role_id in r["role_ids"])
    }
    sources = {d["_id"]: d for d in documents}
    locations = {(s["document_id"], s["section_id"]): s for s in sections}
    counts = Counter(item.requirement_id for item in plan.items)
    quiz_counts = Counter(
        normalized(item.quiz.question).casefold()
        for item in plan.items
        if getattr(item, "quiz", None)
    )
    mandatory = {key for key, r in expected.items() if r["mandatory"]}
    covered, traced = set(), 0
    findings, rows = [], []
    warnings = []
    for index, item in enumerate(plan.items):
        source_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", item.source_quote))
        lesson_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", getattr(item, "lesson", "")))
        if lesson_numbers - source_numbers:
            warnings.append(
                {
                    "code": "UNSUPPORTED_NUMERIC_CLAIM",
                    "requirement_id": item.requirement_id,
                    "message": "Lesson contains numbers absent from its source quote; verify whether these are instructional examples or unsupported policy claims.",
                }
            )
        for previous in plan.items[:index]:
            for field in ("module_title", "practical_activity"):
                left = normalized(getattr(item, field, "")).casefold()
                right = normalized(getattr(previous, field, "")).casefold()
                if left and right and SequenceMatcher(None, left, right).ratio() >= 0.9:
                    warnings.append(
                        {
                            "code": "DUPLICATE_" + field.upper(),
                            "requirement_id": item.requirement_id,
                            "message": f'{field.replace("_", " ")} closely repeats {previous.requirement_id}; review the overlap.',
                        }
                    )
            overlap = {normalized(step).casefold() for step in getattr(item, "checklist", [])} & {
                normalized(step).casefold() for step in getattr(previous, "checklist", [])
            }
            if overlap:
                warnings.append(
                    {
                        "code": "DUPLICATE_CHECKLIST",
                        "requirement_id": item.requirement_id,
                        "message": f"Checklist steps repeat {previous.requirement_id}; review whether repetition is justified.",
                    }
                )
    if len(plan.items) > 1 and all(item.stage == "Day 1" for item in plan.items):
        warnings.append(
            {
                "code": "DAY_ONE_OVERLOAD",
                "message": "All modules are on Day 1; review the staged learning workload.",
            }
        )
    findings.extend(dependency_findings(list(expected.values())))
    for group in conflict_groups(list(expected.values()), role_id):
        findings.append(
            {
                "code": "POLICY_CONFLICT",
                "message": f"Conflicting approved values for {group['key']}. A reviewer must resolve precedence.",
            }
        )
    if plan.role_id != role_id:
        findings.append(
            {"code": "ROLE_MISMATCH", "message": "Plan role differs from the employee role."}
        )
    positions = {item.requirement_id: STAGES.index(item.stage) for item in plan.items}
    for item in plan.items:
        errors = []
        req = expected.get(item.requirement_id)
        doc = sources.get(item.source_document_id)
        section = locations.get((item.source_document_id, item.source_section_id))
        trace = bool(
            doc
            and doc["status"] == "active"
            and section
            and normalized(item.source_quote) in normalized(section["text"])
            and item.source_quote.strip()
        )
        if trace:
            traced += 1
        else:
            errors.append("SOURCE_SUPPORT_MISSING")
        if item.role_id != role_id:
            errors.append("ROLE_MISMATCH")
        if counts[item.requirement_id] > 1:
            errors.append("DUPLICATE_REQUIREMENT")
        if not req:
            errors.append("UNSUPPORTED_REQUIREMENT")
        else:
            if (item.source_document_id, item.source_section_id) != (
                req["document_id"],
                req["section_id"],
            ):
                errors.append("SOURCE_MISMATCH")
            if normalized(item.source_quote) != normalized(req["text"]):
                errors.append("POLICY_TEXT_MISMATCH")
            if item.mandatory != req["mandatory"]:
                errors.append("MANDATORY_MISMATCH")
            if STAGES.index(item.stage) > STAGES.index(req["due_stage"]):
                errors.append("DUE_STAGE_MISSED")
            for prerequisite in req.get("prerequisites", []):
                if (
                    prerequisite not in positions
                    or positions[prerequisite] > positions[item.requirement_id]
                ):
                    errors.append("PREREQUISITE_MISSING_OR_LATE")
            rule = req.get("policy_rule")
            if rule:
                actual = getattr(item, "policy_facts", None)
                if not actual or actual.model_dump() != rule:
                    errors.append("STRUCTURED_RULE_MISMATCH")
                lesson = normalized(getattr(item, "lesson", ""))
                for field in ("condition", "exception"):
                    if rule[field] and normalized(rule[field]) not in lesson:
                        errors.append(field.upper() + "_OMITTED")
                quiz = getattr(item, "quiz", None)
                if rule["answer_fact"] and (
                    not quiz
                    or normalized(quiz.options[quiz.correct_index])
                    != normalized(rule["answer_fact"])
                ):
                    errors.append("QUIZ_ANSWER_FACT_MISMATCH")
            else:
                warnings.append(
                    {
                        "code": "RULE_ANNOTATION_MISSING",
                        "requirement_id": item.requirement_id,
                        "message": "No reviewed structured rule is available. Conditions and answer meaning require human review.",
                    }
                )
            quiz = getattr(item, "quiz", None)
            if quiz and normalized(quiz.evidence_quote) != normalized(req["text"]):
                errors.append("QUIZ_EVIDENCE_MISMATCH")
            if quiz and quiz_counts[normalized(quiz.question).casefold()] > 1:
                warnings.append(
                    {
                        "code": "DUPLICATE_QUIZ",
                        "requirement_id": item.requirement_id,
                        "message": "The same question appears in multiple modules. Review whether this repetition is justified.",
                    }
                )
            if not errors:
                covered.add(item.requirement_id)
        for error in errors:
            findings.append(
                {
                    "code": error,
                    "requirement_id": item.requirement_id,
                    "message": error.replace("_", " ").capitalize(),
                }
            )
        rows.append(
            {
                "requirement_id": item.requirement_id,
                "expected_text": req["text"] if req else "Not in approved role matrix",
                "actual_text": item.source_quote,
                "traceable": trace,
                "result": "Match" if not errors else "Mismatch",
                "errors": errors,
                "verification_status": (
                    "Source Support Missing"
                    if "SOURCE_SUPPORT_MISSING" in errors
                    else (
                        "Unsupported Requirement"
                        if "UNSUPPORTED_REQUIREMENT" in errors
                        else "Manual Review Required" if errors else "Verified with Warning"
                    )
                ),
            }
        )
    for missing in sorted(mandatory - covered):
        findings.append(
            {
                "code": "REQUIREMENT_MISSING",
                "requirement_id": missing,
                "message": "Mandatory requirement has no valid learning item.",
            }
        )
    coverage = round(100 * len(mandatory & covered) / len(mandatory), 1) if mandatory else None
    traceability = round(100 * traced / len(plan.items), 1) if plan.items else None
    if not plan.items:
        findings.append(
            {"code": "EMPTY_PLAN", "message": "The generated plan contains no learning items."}
        )
    # A citation and matching policy quote do not verify all generated prose.
    return {
        "coverage": coverage,
        "traceability": traceability,
        "mandatory_total": len(mandatory),
        "mandatory_covered": len(mandatory & covered),
        "missing_count": len(mandatory - covered),
        "core_passed": not findings,
        "status": "Review required" if not findings else "Needs correction",
        "findings": findings,
        "warnings": warnings,
        "rows": rows,
        "validator_version": "rules-3.0",
        "structured_rules_checked": sum(bool(r.get("policy_rule")) for r in expected.values()),
        "limitation": "Python checks source identity, coverage, structured rule values, quoted conditions/exceptions, approved quiz answer facts, conflicts and prerequisites. Unannotated rules and free-form meaning still require human review; matching evidence is not a proof of semantic correctness.",
    }
