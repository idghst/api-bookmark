import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.routes.health import probe_supabase
from app.core.config import Settings, get_settings
from app.core.errors import ApiError
from app.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        SUPABASE_URL="https://test.supabase.co",
        SUPABASE_PUBLISHABLE_KEY=SecretStr("sb_publishable_test"),
    )


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_production_disables_documentation_and_schema() -> None:
    app = create_app(
        Settings(
            APP_ENV="production",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_PUBLISHABLE_KEY=SecretStr("sb_publishable_test"),
        )
    )
    client = TestClient(app)

    for path in ("/docs", "/redoc", "/openapi.json"):
        response = client.get(path, headers={"X-Request-ID": "req-docs"})

        assert response.status_code == 404
        assert response.json() == {
            "code": "http_error",
            "message": "HTTP error",
            "request_id": "req-docs",
        }


def test_production_exposes_graphql_ide_but_keeps_operations_authenticated() -> None:
    app = create_app(
        Settings(
            APP_ENV="production",
            SUPABASE_URL="https://test.supabase.co",
            SUPABASE_PUBLISHABLE_KEY=SecretStr("sb_publishable_test"),
        )
    )
    client = TestClient(app)

    ide = client.get("/graphql", headers={"Accept": "text/html"})

    assert ide.status_code == 200
    assert "GraphiQL" in ide.text
    assert "isHeadersEditorEnabled: true" in ide.text

    operation = client.post("/graphql", json={"query": "{ status }"})

    assert operation.status_code == 401
    assert operation.json()["code"] == "authentication_required"


def test_factory_injects_supplied_settings(app: FastAPI, settings: Settings) -> None:
    assert app.dependency_overrides[get_settings]() is settings


def test_readiness_maps_upstream_failure(client: TestClient, app: FastAPI) -> None:
    async def unavailable() -> None:
        raise ApiError(503, "dependency_unavailable", "Supabase is unavailable")

    app.dependency_overrides[probe_supabase] = unavailable
    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "dependency_unavailable"
