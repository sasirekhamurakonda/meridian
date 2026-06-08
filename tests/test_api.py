from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.schemas import JobStatus


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_research_validation(client):
    response = await client.post("/research", json={"query": "ab"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_research_not_found(client):
    with patch("app.api.research.async_session_factory") as mock_session_factory:
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=None)
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        response = await client.get(f"/research/{uuid4()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_research_enqueues_job(client):
    with (
        patch("app.api.research.async_session_factory") as mock_session_factory,
        patch("app.api.research.create_pool", new_callable=AsyncMock) as mock_create_pool,
    ):
        mock_session = AsyncMock()

        async def fake_refresh(job):
            pass

        mock_session.add = lambda job: None
        mock_session.commit = AsyncMock()
        mock_session.refresh = fake_refresh
        mock_session_factory.return_value.__aenter__.return_value = mock_session

        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock()
        mock_pool.aclose = AsyncMock()
        mock_create_pool.return_value = mock_pool

        response = await client.post(
            "/research",
            json={"query": "What is quantum error correction?"},
        )

    assert response.status_code == 202
    data = response.json()
    assert data["status"] == JobStatus.QUEUED.value
    assert "id" in data
    mock_pool.enqueue_job.assert_awaited_once()
