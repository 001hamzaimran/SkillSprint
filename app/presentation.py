"""Keep learner API responses free of answer keys, including nested report data."""

from contextvars import ContextVar

response_role = ContextVar("response_role", default=None)


def safe_payload(value):
    if isinstance(value, list):
        return [safe_payload(item) for item in value]
    if not isinstance(value, dict):
        return value
    hidden = {"password_hash", "token_hash"}
    if response_role.get() == "employee":
        hidden |= {"correct_index", "correct_indices", "expected_response", "answer_fact"}
        if "options" in value and "question" in value:
            hidden.add("explanation")
    return {key: safe_payload(item) for key, item in value.items() if key not in hidden}
