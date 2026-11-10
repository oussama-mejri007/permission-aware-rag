from fastapi.testclient import TestClient
from h11 import Request

from app.main import app
from app.main import get_current_user, get_db
from app.main import get_admin_user
from app.main import get_authenticated_user


client = TestClient(app)


def test_rag_endpoint_rejects_missing_token():
    response = client.post(
        "/rag/ask",
        json={"question": "What is the company revenue?"},
    )

    assert response.status_code == 401

def test_rag_endpoint_rejects_invalid_token():
    response = client.post(
        "/rag/ask",
        json={"question": "What is the company revenue?"},
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401

def test_rag_endpoint_rejects_deleted_user():
    class FakeDB:
        def get(self, model, user_id):
            return None

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 9999,
        "tenant_id": 1,
        "role": "admin",
    }
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/rag/ask",
            json={"question": "What is the company revenue?"},
            headers={"Authorization": "Bearer valid-test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401

def test_rag_endpoint_rejects_inactive_user():
    class FakeUser:
        id = 9999
        tenant_id = 1
        role = "admin"
        is_active = False

    class FakeDB:
        def get(self, model, user_id):
            return FakeUser()

    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": 9999,
        "tenant_id": 1,
        "role": "admin",
    }
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/rag/ask",
            json={"question": "What is the company revenue?"},
            headers={"Authorization": "Bearer valid-test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401

def test_login_rejects_inactive_user(monkeypatch):
    from app.main import login
    from app.main import OAuth2PasswordRequestForm
    from starlette.requests import Request

    request = Request({
    "type": "http",
    "method": "POST",
    "path": "/auth/login",
    "headers": [],
    "query_string": b"",
    "server": ("testserver", 80),
    "client": ("127.0.0.1", 50000),
    "scheme": "http",
    })
    class FakeUser:
        id = 9999
        email = "inactive@example.com"
        password_hash = "fake-hash"
        is_active = False

    class FakeDB:
        def scalar(self, query):
            return FakeUser()

    monkeypatch.setattr(
        "app.main.verify_password",
        lambda password, password_hash: True,
    )

    form = OAuth2PasswordRequestForm(
        username="inactive@example.com",
        password="correct-password",
    )

    from fastapi import HTTPException

    try:
        login(request=request, form_data=form, db=FakeDB())
        assert False, "Expected HTTPException"
    except HTTPException as exc:
        assert exc.status_code == 401

def test_users_endpoint_rejects_non_admin():
    class FakeUser:
        id = 10
        tenant_id = 1
        role = "employee"
        is_active = True

    app.dependency_overrides[get_authenticated_user] = lambda: FakeUser()

    try:
        response = client.get(
            "/users",
            headers={"Authorization": "Bearer valid-test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403

def test_admin_sees_only_users_from_own_tenant():
    class FakeUser:
        id = 10
        email = "admin@company-a.com"
        role = "admin"
        is_active = True

    class FakeResult:
        def all(self):
            return [FakeUser()]

    class FakeDB:
        def scalars(self, query):
            compiled_query = query.compile()
            assert 1 in compiled_query.params.values()
            return FakeResult()

    admin = FakeUser()
    admin.tenant_id = 1

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.get(
            "/users",
            headers={"Authorization": "Bearer valid-test-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["email"] == "admin@company-a.com"
    assert "password_hash" not in response.json()[0]

def test_admin_can_create_user(monkeypatch):
    class FakeUser:
        id = 20
        tenant_id = 1
        email = "newuser@company-a.com"
        role = "employee"
        is_active = True

    class FakeDB:
        def scalar(self, query):
            return None

        def add(self, user):
            self.user = user
            assert user.tenant_id == 1
            assert user.email == "newuser@company-a.com"
            assert user.role == "employee"
            assert user.password_hash != "StrongPassword123!"

        def commit(self):
            pass

        def refresh(self, user):
            user.id = 20

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    fake_db = FakeDB()

    monkeypatch.setattr(
        "app.main.hash_password",
        lambda password: "hashed-password",
    )

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        response = client.post(
            "/users",
            json={
                "email": "newuser@company-a.com",
                "password": "StrongPassword123!",
                "role": "employee",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["id"] == 20
    assert response.json()["email"] == "newuser@company-a.com"
    assert response.json()["role"] == "employee"
    assert "password_hash" not in response.json()

def test_admin_cannot_create_user_with_existing_email():
    class FakeDB:
        def scalar(self, query):
            return object()

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/users",
            json={
                "email": "existing@company-a.com",
                "password": "StrongPassword123!",
                "role": "employee",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409

def test_create_user_rejects_invalid_role_and_short_password():
    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    app.dependency_overrides[get_admin_user] = lambda: admin

    try:
        invalid_role = client.post(
            "/users",
            json={
                "email": "user@company-a.com",
                "password": "StrongPassword123!",
                "role": "admin",
            },
        )

        short_password = client.post(
            "/users",
            json={
                "email": "user@company-a.com",
                "password": "short",
                "role": "employee",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert invalid_role.status_code == 422
    assert short_password.status_code == 422

def test_admin_can_deactivate_user():
    class FakeUser:
        id = 20
        tenant_id = 1
        email = "employee@company-a.com"
        role = "employee"
        is_active = True

    fake_user = FakeUser()

    class FakeDB:
        def scalar(self, query):
            return fake_user

        def commit(self):
            assert fake_user.is_active is False

        def refresh(self, user):
            pass

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.patch(
            "/users/20",
            json={"is_active": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["is_active"] is False

def test_admin_cannot_update_user_from_another_tenant():
    class FakeDB:
        def scalar(self, query):
            compiled = query.compile()
            params = compiled.params

            assert 1 in params.values()  # Tenant de l'admin
            assert 20 in params.values()  # ID de l'utilisateur

            return None

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.patch(
            "/users/20",
            json={"is_active": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404

def test_admin_cannot_update_another_admin():
    class FakeUser:
        id = 20
        tenant_id = 1
        email = "admin2@company-a.com"
        role = "admin"
        is_active = True

    fake_user = FakeUser()

    class FakeDB:
        def scalar(self, query):
            return fake_user

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.patch(
            "/users/20",
            json={"is_active": False},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert fake_user.is_active is True

def test_admin_can_delete_user():
    class FakeUser:
        id = 20
        tenant_id = 1
        email = "employee@company-a.com"
        role = "employee"
        is_active = True

    fake_user = FakeUser()

    class FakeDB:
        deleted_user = None

        def scalar(self, query):
            return fake_user

        def delete(self, user):
            self.deleted_user = user
            assert user.id == 20

        def commit(self):
            assert self.deleted_user is fake_user

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    fake_db = FakeDB()

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        response = client.delete("/users/20")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""
    assert fake_db.deleted_user is fake_user

def test_admin_cannot_delete_user_from_another_tenant():
    class FakeDB:
        def scalar(self, query):
            compiled = query.compile()
            params = compiled.params

            assert 1 in params.values()
            assert 20 in params.values()

            return None

        def delete(self, user):
            raise AssertionError("User should not be deleted")

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.delete("/users/20")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404

def test_admin_cannot_delete_another_admin():
    class FakeUser:
        id = 20
        tenant_id = 1
        email = "admin2@company-a.com"
        role = "admin"
        is_active = True

    fake_user = FakeUser()

    class FakeDB:
        def scalar(self, query):
            return fake_user

        def delete(self, user):
            raise AssertionError("Admin should not be deleted")

    admin = type(
        "FakeAdmin",
        (),
        {"id": 10, "tenant_id": 1, "role": "admin", "is_active": True},
    )()

    app.dependency_overrides[get_admin_user] = lambda: admin
    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.delete("/users/20")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403

def test_login_rate_limit(monkeypatch):
    class FakeDB:
        def scalar(self, query):
            return None

    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        responses = [
            client.post(
                "/auth/login",
                data={
                    "username": "unknown@example.com",
                    "password": "wrong-password",
                },
            )
            for _ in range(6)
        ]
    finally:
        app.dependency_overrides.clear()

    assert all(response.status_code == 401 for response in responses[:5])
    assert responses[5].status_code == 429

import pytest
from pydantic import ValidationError
from app.main import UserCreate


@pytest.mark.parametrize(
    "password",
    [
        "alllowercase123!",
        "ALLUPPERCASE123!",
        "NoDigitsHere!!",
        "NoSpecialChar123",
        "Short1!",
    ],
)
def test_user_creation_rejects_weak_passwords(password):
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            password=password,
            role="employee",
        )


def test_user_creation_accepts_strong_password():
    user = UserCreate(
        email="test@example.com",
        password="StrongPassword123!",
        role="employee",
    )

    assert user.password == "StrongPassword123!"


def test_refresh_token_rotates_tokens(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from app.models.models import RefreshToken

    old_token = RefreshToken(
        id=1,
        user_id=20,
        token_hash="old-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=None,
    )

    class FakeUser:
        id = 20
        tenant_id = 1
        role = "employee"
        is_active = True

    fake_user = FakeUser()

    class FakeDB:
        def __init__(self):
            self.added = None
            self.committed = False

        def scalar(self, query):
            return old_token

        def get(self, model, user_id):
            return fake_user

        def add(self, obj):
            self.added = obj

        def commit(self):
            self.committed = True

    fake_db = FakeDB()

    monkeypatch.setattr(
        "app.main.hash_refresh_token",
        lambda token: "old-hash",
    )
    monkeypatch.setattr(
        "app.main.create_refresh_token",
        lambda: "new-refresh-token",
    )
    monkeypatch.setattr(
        "app.main.hash_refresh_token",
        lambda token: "new-hash" if token == "new-refresh-token" else "old-hash",
    )
    monkeypatch.setattr(
        "app.main.create_access_token",
        lambda **kwargs: "new-access-token",
    )

    app.dependency_overrides[get_db] = lambda: fake_db

    try:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "old-refresh-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["access_token"] == "new-access-token"
    assert response.json()["refresh_token"] == "new-refresh-token"
    assert old_token.revoked_at is not None
    assert fake_db.added.token_hash == "new-hash"
    assert fake_db.committed is True


def test_refresh_token_rejects_revoked_token(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from app.models.models import RefreshToken

    revoked_token = RefreshToken(
        id=1,
        user_id=20,
        token_hash="old-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=datetime.now(timezone.utc),
    )

    class FakeDB:
        def scalar(self, query):
            return revoked_token

    monkeypatch.setattr(
        "app.main.hash_refresh_token",
        lambda token: "old-hash",
    )

    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "old-refresh-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401


def test_refresh_token_rejects_expired_token(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from app.models.models import RefreshToken

    expired_token = RefreshToken(
        id=1,
        user_id=20,
        token_hash="old-hash",
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        revoked_at=None,
    )

    class FakeDB:
        def scalar(self, query):
            return expired_token

    monkeypatch.setattr(
        "app.main.hash_refresh_token",
        lambda token: "old-hash",
    )

    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "expired-refresh-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401

def test_refresh_token_rejects_unknown_token(monkeypatch):
    class FakeDB:
        def scalar(self, query):
            return None

    monkeypatch.setattr(
        "app.main.hash_refresh_token",
        lambda token: "unknown-hash",
    )

    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "unknown-refresh-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401

def test_refresh_token_rejects_unknown_token(monkeypatch):
    class FakeDB:
        def scalar(self, query):
            return None

    monkeypatch.setattr(
        "app.main.hash_refresh_token",
        lambda token: "unknown-hash",
    )

    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "unknown-refresh-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401

def test_refresh_token_rejects_inactive_user(monkeypatch):
    from datetime import datetime, timezone, timedelta
    from app.models.models import RefreshToken

    valid_token = RefreshToken(
        id=1,
        user_id=20,
        token_hash="old-hash",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        revoked_at=None,
    )

    class FakeUser:
        id = 20
        tenant_id = 1
        role = "employee"
        is_active = False

    class FakeDB:
        def scalar(self, query):
            return valid_token

        def get(self, model, user_id):
            return FakeUser()

    monkeypatch.setattr(
        "app.main.hash_refresh_token",
        lambda token: "old-hash",
    )

    app.dependency_overrides[get_db] = lambda: FakeDB()

    try:
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": "old-refresh-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
