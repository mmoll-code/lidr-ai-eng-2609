"""HTTP tests for app metadata, health, and OpenAPI docs."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealth:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client) -> None:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestOpenApiMetadata:
    @pytest.mark.asyncio
    async def test_openapi_info_fields(self, client) -> None:
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        info = response.json()["info"]
        assert info["title"] == "Estimador CAG API"
        assert info["description"]
        assert info["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_openapi_paths_include_estimate_and_health(self, client) -> None:
        response = await client.get("/openapi.json")
        paths = response.json()["paths"]
        assert "/api/v1/estimate" in paths
        assert "/health" in paths

    @pytest.mark.asyncio
    async def test_docs_available(self, client) -> None:
        response = await client.get("/docs")
        assert response.status_code == 200
