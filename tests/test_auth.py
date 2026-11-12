
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import pytest

from app.auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
)
from app.auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
    JWT_EXPIRE_MINUTES,
)

@pytest.fixture
def jwt_secret(monkeypatch):
    secret = "test-secret-key-for-jwt-tests-32-bytes-minimum"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)
    return secret


def test_create_and_decode_valid_token(jwt_secret):
    token = create_access_token(
        user_id=1,
        tenant_id=1,
        role="admin",
        token_version=0,
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["tenant_id"] == 1
    assert payload["role"] == "admin"

def test_access_token_expires_after_configured_duration(jwt_secret):
    token = create_access_token(
        user_id=1,
        tenant_id=1,
        role="admin",
        token_version=0,
    )

    payload = decode_access_token(token)

    issued_at = datetime.fromtimestamp(payload["iat"], timezone.utc)
    expires_at = datetime.fromtimestamp(payload["exp"], timezone.utc)

    duration = expires_at - issued_at

    assert duration == timedelta(minutes=JWT_EXPIRE_MINUTES)
    assert JWT_EXPIRE_MINUTES == 30


def test_expired_token_is_rejected(jwt_secret):
    payload = {
        "sub": "1",
        "tenant_id": 1,
        "role": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }

    token = jwt.encode(
        payload,
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401


def test_invalid_signature_is_rejected(jwt_secret):
    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": 1,
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        "another-test-secret-key-for-jwt-32-bytes",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401


def test_token_without_tenant_id_is_rejected(jwt_secret):
    token = jwt.encode(
        {
            "sub": "1",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401


def test_token_without_role_is_rejected(jwt_secret):
    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": 1,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401

def test_token_with_invalid_user_id_is_rejected(jwt_secret):
    token = jwt.encode(
        {
            "sub": "abc",
            "tenant_id": 1,
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401

def test_token_with_invalid_tenant_id_is_rejected(jwt_secret):
    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": "abc",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401

def test_token_with_boolean_tenant_id_is_rejected(jwt_secret):
    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": True,
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        jwt_secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401

def test_malformed_token_is_rejected(jwt_secret):
    malformed_token = "this-is-not-a-valid-jwt"

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=malformed_token)

    assert exc_info.value.status_code == 401
