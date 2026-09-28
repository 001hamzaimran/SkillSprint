"""Server authorization behind the assistant's allowlisted existing tools."""

from .test_srs_completion import sign_in


def test_assistant_library_and_activation_permissions(workspace):
    client, db, _ = workspace
    db.documents.insert_one({
        "_id": "assistant-source", "document_id": "ASSIST-01", "title": "Assistant test source",
        "version": "1", "effective_date": "2025-01-01", "category": "Policy",
        "status": "draft", "suspicious": False,
    })
    assert client.get('/api/documents').status_code == 401
    for role in ('employee', 'manager'):
        headers = sign_in(client, role)
        assert client.get('/api/documents').status_code == 403
        assert client.get('/api/documents/assistant-source').status_code == 403
        assert client.post('/api/documents/assistant-source/activate', headers=headers).status_code == 403
    headers = sign_in(client, 'training_manager')
    assert client.get('/api/documents').status_code == 200
    assert client.post('/api/documents/assistant-source/activate', headers=headers).status_code == 403
    headers = sign_in(client, 'reviewer')
    assert client.post('/api/documents/assistant-source/activate').status_code == 403
    assert db.documents.find_one({'_id': 'assistant-source'})['status'] == 'draft'
    activated = client.post('/api/documents/assistant-source/activate', headers=headers)
    assert activated.status_code == 204
    assert activated.content == b''
    assert db.documents.find_one({'_id': 'assistant-source'})['status'] == 'active'


def test_assistant_activation_respects_quarantine(workspace):
    client, db, _ = workspace
    db.documents.insert_one({
        "_id": "unsafe-source", "document_id": "UNSAFE-01", "title": "Quarantined test",
        "version": "1", "effective_date": "2025-01-01", "status": "draft", "suspicious": True,
    })
    headers = sign_in(client)
    assert client.post('/api/documents/unsafe-source/activate', headers=headers).status_code == 422
    assert db.documents.find_one({'_id': 'unsafe-source'})['status'] == 'draft'
