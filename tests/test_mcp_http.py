import pytest
from starlette.testclient import TestClient

from nutrition_mcp.mcp_http_server import create_app


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as client:
        yield client


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_mcp_endpoint_rejects_get_without_headers(client):
    response = client.get("/mcp")
    assert response.status_code in (400, 404, 405, 406)
