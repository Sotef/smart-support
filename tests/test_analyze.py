from fastapi.testclient import TestClient
from app.main import app


def test_analyze_basic():
    with TestClient(app) as client:
        payload = {
            "request_id": "req_test",
            "text": "У меня не получается войти. Ошибка 404. Мой номер +7 (900) 123-45-67",
            "channel": "web",
        }
        resp = client.post("/api/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("request_id") == "req_test"
        assert "classification" in data
        assert "entities" in data
        assert "suggested_responses" in data
