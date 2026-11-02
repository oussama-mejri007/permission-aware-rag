from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_rag_endpoint_rejects_missing_token():
    response = client.post(
        "/rag/ask",
        json={"question": "What is the company revenue?"},
    )

    assert response.status_code == 401