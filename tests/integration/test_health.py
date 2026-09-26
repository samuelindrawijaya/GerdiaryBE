from uuid import UUID

from flask.testing import FlaskClient


def test_health_uses_success_envelope_and_request_id(client: FlaskClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json == {"data": {"status": "available"}, "meta": {}}
    UUID(response.headers["X-Request-ID"])


def test_unknown_route_uses_error_envelope(client: FlaskClient) -> None:
    response = client.get("/api/v1/missing")

    assert response.status_code == 404
    assert response.json["error"]["code"] == "not_found"
    assert response.json["error"]["fields"] == {}
    assert response.json["error"]["request_id"] == response.headers["X-Request-ID"]
