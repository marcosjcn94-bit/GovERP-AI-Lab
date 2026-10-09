from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from gov_erp import api


def test_database_failure_is_sanitized_and_measured(monkeypatch, caplog):
    def unavailable():
        raise OperationalError("private SQL", {}, Exception("private DSN"))

    measurements = []
    monkeypatch.setattr(api, "OwnerSession", unavailable)
    monkeypatch.setattr(api, "record_http_request", lambda *args: measurements.append(args))
    with caplog.at_level("INFO", logger="gov_erp.api"):
        response = TestClient(api.app).get("/api/public/municipalities")
    assert response.status_code == 503
    assert response.json() == {"detail": "Banco local indisponivel"}
    assert response.headers["x-request-id"]
    assert measurements[0][1:3] == ("/api/public/municipalities", 503)
    assert measurements[0][3] >= 0
    assert "private" not in caplog.text
    assert caplog.records[-1].request_id == response.headers["x-request-id"]
