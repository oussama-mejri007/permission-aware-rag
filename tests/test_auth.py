
import jwt
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
import pytest

from app.auth import (
    create_access_token,
    decode_access_token,
    get_current_user,
)


def test_create_and_decode_valid_token(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-jwt-tests-32-bytes-minimum")

    token = create_access_token(
        user_id=1,
        tenant_id=1,
        role="admin",
    )

    payload = decode_access_token(token)

    assert payload["sub"] == "1"
    assert payload["tenant_id"] == 1
    assert payload["role"] == "admin"


def test_expired_token_is_rejected(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-jwt-tests-32-bytes-minimum",
    )

    payload = {
        "sub": "1",
        "tenant_id": 1,
        "role": "admin",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }

    token = jwt.encode(
        payload,
        "test-secret-key-for-jwt-tests-32-bytes-minimum",
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401


def test_invalid_signature_is_rejected(monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "test-secret-key-for-jwt-tests-32-bytes-minimum",
    )

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


def test_token_without_tenant_id_is_rejected(monkeypatch):
    secret = "test-secret-key-for-jwt-tests-32-bytes-minimum"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    token = jwt.encode(
        {
            "sub": "1",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401


def test_token_without_role_is_rejected(monkeypatch):
    secret = "test-secret-key-for-jwt-tests-32-bytes-minimum"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": 1,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401

def test_token_with_invalid_user_id_is_rejected(monkeypatch):
    secret = "test-secret-key-for-jwt-tests-32-bytes-minimum"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    token = jwt.encode(
        {
            "sub": "abc",
            "tenant_id": 1,
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401

def test_token_with_invalid_tenant_id_is_rejected(monkeypatch):
    secret = "test-secret-key-for-jwt-tests-32-bytes-minimum"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": "abc",
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401

def test_token_with_boolean_tenant_id_is_rejected(monkeypatch):
    secret = "test-secret-key-for-jwt-tests-32-bytes-minimum"
    monkeypatch.setenv("JWT_SECRET_KEY", secret)

    token = jwt.encode(
        {
            "sub": "1",
            "tenant_id": True,
            "role": "admin",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        secret,
        algorithm="HS256",
    )

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(token=token)

    assert exc_info.value.status_code == 401
