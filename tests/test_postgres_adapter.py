from app.db import _apply_update, _matches, now


def test_document_query_and_update_semantics():
    document = {
        "_id": "1",
        "role_ids": ["support"],
        "count": 1,
        "nested": {"state": "old"},
        "created_at": now(),
    }
    assert _matches(document, {"role_ids": "support"})
    assert _matches(document, {"_id": {"$in": ["1", "2"]}})
    assert _matches(document, {"count": {"$lt": 3}})
    assert _matches(document, {"$or": [{"count": 9}, {"nested.state": "old"}]})
    changed = _apply_update(
        document,
        {
            "$set": {"nested.state": "new"},
            "$inc": {"count": 2},
            "$push": {"items": "x"},
            "$unset": {"missing": ""},
        },
    )
    assert changed["count"] == 3
    assert changed["nested"]["state"] == "new"
    assert changed["items"] == ["x"]
