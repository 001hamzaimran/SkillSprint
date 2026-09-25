import hashlib
import hmac
import secrets
from datetime import timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError
from fastapi import HTTPException
from .db import now, uid

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
ROLES = {'admin', 'training_manager', 'reviewer', 'manager', 'employee'}
EDITORS = {'admin', 'training_manager'}
REVIEWERS = {'admin', 'reviewer'}


def hash_password(password):
    if len(password) < 12 or len(password) > 128:
        raise ValueError('Use a password between 12 and 128 characters.')
    return hasher.hash(password)


def verify_password(password, encoded):
    if len(password) > 128:
        return False
    try:
        return hasher.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def token_hash(value):
    return hashlib.sha256(value.encode()).hexdigest()


def anonymous_csrf(secret):
    nonce = secrets.token_urlsafe(24)
    return nonce + '.' + hmac.new(secret.encode(), nonce.encode(), hashlib.sha256).hexdigest()


def valid_anonymous(token, cookie, secret):
    if not token or not cookie or not hmac.compare_digest(token, cookie):
        return False
    parts = token.split('.')
    if len(parts) != 2:
        return False
    expected = hmac.new(secret.encode(), parts[0].encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, parts[1])


def new_session(db, user_id):
    token = secrets.token_urlsafe(48)
    session = {'_id': uid(), 'token_hash': token_hash(token), 'user_id': user_id,
        'csrf': secrets.token_urlsafe(32), 'expires_at': now() + timedelta(hours=8)}
    db.sessions.insert_one(session)
    return token


def identity(request):
    token = request.cookies.get('skillsprint_session', '')
    if not token:
        return None, None
    session = request.app.state.db.sessions.find_one({'token_hash': token_hash(token), 'expires_at': {'$gt': now()}})
    user = request.app.state.db.users.find_one({'_id': session['user_id'], 'active': True}) if session else None
    return user, session


def require(request, roles=None):
    user, session = identity(request)
    if not user:
        raise HTTPException(401, 'Please sign in to continue.')
    if roles and user['role'] not in roles:
        raise HTTPException(403, 'Your account does not have permission for this action.')
    return user, session


def csrf(request, session, token):
    if not token or not hmac.compare_digest(session['csrf'], token):
        raise HTTPException(403, 'This form expired. Refresh the page and try again.')


def can_read_employee(user, employee):
    return (user['role'] in {'admin', 'training_manager', 'reviewer'} or
            (user['role'] == 'manager' and employee.get('manager_id') == user['_id']) or
            (user['role'] == 'employee' and employee.get('user_id') == user['_id']))
