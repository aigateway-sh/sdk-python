"""Smoke tests for the sync + async clients using httpx MockTransport."""

from __future__ import annotations

import asyncio
import json
from typing import Dict, List

import httpx
import pytest

from aigateway import AIgateway, AsyncAIgateway, AIgatewayError


def _mock_transport(calls: List[Dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({
            "method": request.method,
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": request.content.decode() if request.content else "",
        })
        if request.url.path.endswith("/v1/videos/generations"):
            return httpx.Response(202, json={"id": "job_1", "status": "queued", "modality": "video", "created_at": 1, "updated_at": 1})
        if "/v1/jobs/job_1" in request.url.path and request.method == "GET":
            return httpx.Response(200, json={"id": "job_1", "status": "completed", "modality": "video", "created_at": 1, "updated_at": 2, "result_url": "https://r2/x.mp4"})
        if "/v1/models/unknown" in request.url.path:
            return httpx.Response(404, json={"error": {"message": "Model not found", "type": "model_not_found", "code": 404}})
        if request.url.path.endswith("/v1/models"):
            return httpx.Response(200, json={"object": "list", "data": [{"id": "openai/gpt-5.2"}]})
        return httpx.Response(200, json={})
    return httpx.MockTransport(handler)


def test_sync_client_headers_and_body():
    calls: List[Dict] = []
    client = AIgateway(api_key="sk-aig-test", tag="feature-x", transport=_mock_transport(calls))
    job = client.jobs.create_video(prompt="a cat")
    assert job.id == "job_1"
    assert calls[0]["headers"]["authorization"] == "Bearer sk-aig-test"
    assert calls[0]["headers"]["x-aig-tag"] == "feature-x"
    assert json.loads(calls[0]["body"])["prompt"] == "a cat"
    client.close()


def test_sync_client_error_mapping():
    calls: List[Dict] = []
    client = AIgateway(api_key="k", transport=_mock_transport(calls))
    with pytest.raises(AIgatewayError) as exc:
        client.models.get("unknown")
    assert exc.value.status_code == 404
    assert exc.value.type == "model_not_found"
    client.close()


def test_sync_wait_returns_completed_job():
    calls: List[Dict] = []
    client = AIgateway(api_key="k", transport=_mock_transport(calls))
    job = client.jobs.wait("job_1", poll_interval_seconds=0.01, timeout_seconds=5)
    assert job.status == "completed"
    assert job.result_url == "https://r2/x.mp4"
    client.close()


def test_sync_models_list_query_params():
    calls: List[Dict] = []
    client = AIgateway(api_key="k", transport=_mock_transport(calls))
    client.models.list(modality="image", provider="bfl")
    assert "modality=image" in calls[-1]["url"]
    assert "provider=bfl" in calls[-1]["url"]
    client.close()


@pytest.mark.asyncio
async def test_async_client_headers_and_body():
    calls: List[Dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"method": request.method, "url": str(request.url), "headers": dict(request.headers), "body": request.content.decode() if request.content else ""})
        return httpx.Response(202, json={"id": "job_a", "status": "queued", "modality": "video", "created_at": 1, "updated_at": 1})

    async with AsyncAIgateway(api_key="sk-aig-async", transport=httpx.MockTransport(handler)) as client:
        job = await client.jobs.create_video(prompt="a cat")
    assert job.id == "job_a"
    assert calls[0]["headers"]["authorization"] == "Bearer sk-aig-async"
