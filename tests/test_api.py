from fastapi.testclient import TestClient

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
        login(form_data=form, db=FakeDB())
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