from fastapi.testclient import TestClient

from app.main import app
from app.main import get_current_user, get_db


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