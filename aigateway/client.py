"""Sync + async HTTP clients for AIgateway."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional

import httpx


DEFAULT_BASE_URL = "https://api.aigateway.sh"
DEFAULT_MEDIA_BASE_URL = "https://media.aigateway.sh"
VERSION = "0.1.2"


class AIgatewayError(Exception):
    """Raised for any non-2xx response from the gateway."""

    def __init__(self, message: str, status_code: int, type_: str = "api_error") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.type = type_


@dataclass
class Job:
    id: str
    status: str
    modality: str
    model: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[int] = None
    result_url: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Job":
        return cls(
            id=d["id"],
            status=d["status"],
            modality=d.get("modality", ""),
            model=d.get("model"),
            created_at=d.get("created_at"),
            updated_at=d.get("updated_at"),
            result_url=d.get("result_url"),
            result=d.get("result"),
            error=d.get("error"),
            raw=d,
        )


def _build_headers(api_key: str, tag: Optional[str]) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": f"aigateway-python/{VERSION}",
    }
    if tag:
        headers["x-aig-tag"] = tag
    return headers


def _raise_from_response(resp: httpx.Response) -> None:
    try:
        payload = resp.json()
    except Exception:
        raise AIgatewayError(f"HTTP {resp.status_code}: {resp.text[:200]}", resp.status_code)
    err = (payload or {}).get("error") or {}
    raise AIgatewayError(
        err.get("message") or f"HTTP {resp.status_code}",
        resp.status_code,
        err.get("type") or "api_error",
    )


class AIgateway:
    """Synchronous client. Use ``AsyncAIgateway`` from asyncio code."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        media_base_url: str = DEFAULT_MEDIA_BASE_URL,
        tag: Optional[str] = None,
        timeout: float = 60.0,
        transport: Optional[httpx.BaseTransport] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.base_url = base_url.rstrip("/")
        self.media_base_url = media_base_url.rstrip("/")
        self.api_key = api_key
        self.tag = tag
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=_build_headers(api_key, tag),
            timeout=timeout,
            transport=transport,
        )
        # Separate client for the media subdomain so downloads never hit
        # api.aigateway.sh. Same auth header / timeout.
        self._media_client = httpx.Client(
            base_url=self.media_base_url,
            headers=_build_headers(api_key, tag),
            timeout=timeout,
            transport=transport,
        )

        self.jobs = _Jobs(self)
        self.sub_accounts = _SubAccounts(self)
        self.evals = _Evals(self)
        self.replays = _Replays(self)
        self.files = _Files(self)
        self.webhook_secret = _WebhookSecret(self)
        self.models = _Models(self)

    def __enter__(self) -> "AIgateway":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()
        self._media_client.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Any] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        resp = self._client.request(method, path, json=json, params=params)
        if resp.is_error:
            _raise_from_response(resp)
        return resp.json() if resp.content else None


class AsyncAIgateway:
    """Async variant backed by ``httpx.AsyncClient``."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        media_base_url: str = DEFAULT_MEDIA_BASE_URL,
        tag: Optional[str] = None,
        timeout: float = 60.0,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        self.base_url = base_url.rstrip("/")
        self.media_base_url = media_base_url.rstrip("/")
        self.api_key = api_key
        self.tag = tag
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=_build_headers(api_key, tag),
            timeout=timeout,
            transport=transport,
        )
        self._media_client = httpx.AsyncClient(
            base_url=self.media_base_url,
            headers=_build_headers(api_key, tag),
            timeout=timeout,
            transport=transport,
        )

        self.jobs = _AsyncJobs(self)
        self.sub_accounts = _AsyncSubAccounts(self)
        self.evals = _AsyncEvals(self)
        self.replays = _AsyncReplays(self)
        self.files = _AsyncFiles(self)
        self.webhook_secret = _AsyncWebhookSecret(self)
        self.models = _AsyncModels(self)

    async def __aenter__(self) -> "AsyncAIgateway":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()
        await self._media_client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[Any] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> Any:
        resp = await self._client.request(method, path, json=json, params=params)
        if resp.is_error:
            _raise_from_response(resp)
        return resp.json() if resp.content else None


# ============ RESOURCE CLASSES (sync) ============

class _Jobs:
    def __init__(self, client: AIgateway) -> None:
        self._c = client

    def create_video(self, **kwargs: Any) -> Job:
        return Job.from_dict(self._c._request("POST", "/v1/videos/generations", json=kwargs))

    def create_music(self, **kwargs: Any) -> Job:
        return Job.from_dict(self._c._request("POST", "/v1/audio/music", json=kwargs))

    def create_3d(self, **kwargs: Any) -> Job:
        return Job.from_dict(self._c._request("POST", "/v1/3d/generations", json=kwargs))

    def get(self, job_id: str) -> Job:
        return Job.from_dict(self._c._request("GET", f"/v1/jobs/{job_id}"))

    def cancel(self, job_id: str) -> Job:
        return Job.from_dict(self._c._request("DELETE", f"/v1/jobs/{job_id}"))

    def wait(
        self,
        job_id: str,
        *,
        timeout_seconds: float = 600.0,
        poll_interval_seconds: float = 2.0,
    ) -> Job:
        start = time.time()
        delay = poll_interval_seconds
        while True:
            job = self.get(job_id)
            if job.status in ("completed", "failed"):
                return job
            if time.time() - start > timeout_seconds:
                raise AIgatewayError(
                    f"Job {job_id} did not complete within {timeout_seconds}s",
                    408,
                    "timeout_error",
                )
            time.sleep(delay)
            delay = min(delay * 1.5, 30.0)


class _SubAccounts:
    def __init__(self, client: AIgateway) -> None:
        self._c = client

    def create(self, **kwargs: Any) -> Dict[str, Any]:
        return self._c._request("POST", "/v1/sub-accounts", json=kwargs)

    def list(self) -> List[Dict[str, Any]]:
        return self._c._request("GET", "/v1/sub-accounts").get("data", [])

    def get(self, id: str) -> Dict[str, Any]:
        return self._c._request("GET", f"/v1/sub-accounts/{id}")

    def delete(self, id: str) -> Dict[str, Any]:
        return self._c._request("DELETE", f"/v1/sub-accounts/{id}")


class _Evals:
    def __init__(self, client: AIgateway) -> None:
        self._c = client

    def create(self, **kwargs: Any) -> Dict[str, Any]:
        return self._c._request("POST", "/v1/evals", json=kwargs)

    def list(self) -> List[Dict[str, Any]]:
        return self._c._request("GET", "/v1/evals").get("data", [])

    def get(self, id: str) -> Dict[str, Any]:
        return self._c._request("GET", f"/v1/evals/{id}")


class _Replays:
    def __init__(self, client: AIgateway) -> None:
        self._c = client

    def run(self, **kwargs: Any) -> Dict[str, Any]:
        return self._c._request("POST", "/v1/replays", json=kwargs)

    def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._c._request("GET", "/v1/replays", params={"limit": limit}).get("data", [])

    def get(self, id: str) -> Dict[str, Any]:
        return self._c._request("GET", f"/v1/replays/{id}")


class _Files:
    def __init__(self, client: AIgateway) -> None:
        self._c = client

    def download(self, job_id: str, filename: str) -> bytes:
        # Served from media.aigateway.sh — never the API host.
        resp = self._c._media_client.get(f"/v1/files/jobs/{job_id}/{filename}")
        if resp.is_error:
            _raise_from_response(resp)
        return resp.content

    def signed_url(self, job_id: str, filename: str, expires_in: int = 3600) -> Dict[str, Any]:
        return self._c._request(
            "GET",
            f"/v1/files/jobs/{job_id}/{filename}/signed",
            params={"expires_in": expires_in},
        )


class _WebhookSecret:
    def __init__(self, client: AIgateway) -> None:
        self._c = client

    def get(self) -> Dict[str, Any]:
        return self._c._request("GET", "/v1/webhook-secret")

    def rotate(self) -> Dict[str, Any]:
        return self._c._request("POST", "/v1/webhook-secret/rotate")


class _Models:
    def __init__(self, client: AIgateway) -> None:
        self._c = client

    def list(self, *, modality: Optional[str] = None, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {k: v for k, v in {"modality": modality, "provider": provider}.items() if v}
        return self._c._request("GET", "/v1/models", params=params).get("data", [])

    def get(self, id: str) -> Dict[str, Any]:
        return self._c._request("GET", f"/v1/models/{id}")


# ============ RESOURCE CLASSES (async) ============

class _AsyncJobs:
    def __init__(self, client: AsyncAIgateway) -> None:
        self._c = client

    async def create_video(self, **kwargs: Any) -> Job:
        return Job.from_dict(await self._c._request("POST", "/v1/videos/generations", json=kwargs))

    async def create_music(self, **kwargs: Any) -> Job:
        return Job.from_dict(await self._c._request("POST", "/v1/audio/music", json=kwargs))

    async def create_3d(self, **kwargs: Any) -> Job:
        return Job.from_dict(await self._c._request("POST", "/v1/3d/generations", json=kwargs))

    async def get(self, job_id: str) -> Job:
        return Job.from_dict(await self._c._request("GET", f"/v1/jobs/{job_id}"))

    async def cancel(self, job_id: str) -> Job:
        return Job.from_dict(await self._c._request("DELETE", f"/v1/jobs/{job_id}"))

    async def wait(
        self,
        job_id: str,
        *,
        timeout_seconds: float = 600.0,
        poll_interval_seconds: float = 2.0,
    ) -> Job:
        start = asyncio.get_event_loop().time()
        delay = poll_interval_seconds
        while True:
            job = await self.get(job_id)
            if job.status in ("completed", "failed"):
                return job
            if asyncio.get_event_loop().time() - start > timeout_seconds:
                raise AIgatewayError(
                    f"Job {job_id} did not complete within {timeout_seconds}s",
                    408,
                    "timeout_error",
                )
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 30.0)


class _AsyncSubAccounts:
    def __init__(self, client: AsyncAIgateway) -> None:
        self._c = client

    async def create(self, **kwargs: Any) -> Dict[str, Any]:
        return await self._c._request("POST", "/v1/sub-accounts", json=kwargs)

    async def list(self) -> List[Dict[str, Any]]:
        out = await self._c._request("GET", "/v1/sub-accounts")
        return out.get("data", [])

    async def get(self, id: str) -> Dict[str, Any]:
        return await self._c._request("GET", f"/v1/sub-accounts/{id}")

    async def delete(self, id: str) -> Dict[str, Any]:
        return await self._c._request("DELETE", f"/v1/sub-accounts/{id}")


class _AsyncEvals:
    def __init__(self, client: AsyncAIgateway) -> None:
        self._c = client

    async def create(self, **kwargs: Any) -> Dict[str, Any]:
        return await self._c._request("POST", "/v1/evals", json=kwargs)

    async def list(self) -> List[Dict[str, Any]]:
        return (await self._c._request("GET", "/v1/evals")).get("data", [])

    async def get(self, id: str) -> Dict[str, Any]:
        return await self._c._request("GET", f"/v1/evals/{id}")


class _AsyncReplays:
    def __init__(self, client: AsyncAIgateway) -> None:
        self._c = client

    async def run(self, **kwargs: Any) -> Dict[str, Any]:
        return await self._c._request("POST", "/v1/replays", json=kwargs)

    async def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        return (await self._c._request("GET", "/v1/replays", params={"limit": limit})).get("data", [])

    async def get(self, id: str) -> Dict[str, Any]:
        return await self._c._request("GET", f"/v1/replays/{id}")


class _AsyncFiles:
    def __init__(self, client: AsyncAIgateway) -> None:
        self._c = client

    async def download(self, job_id: str, filename: str) -> bytes:
        resp = await self._c._media_client.get(f"/v1/files/jobs/{job_id}/{filename}")
        if resp.is_error:
            _raise_from_response(resp)
        return resp.content

    async def signed_url(self, job_id: str, filename: str, expires_in: int = 3600) -> Dict[str, Any]:
        return await self._c._request(
            "GET",
            f"/v1/files/jobs/{job_id}/{filename}/signed",
            params={"expires_in": expires_in},
        )


class _AsyncWebhookSecret:
    def __init__(self, client: AsyncAIgateway) -> None:
        self._c = client

    async def get(self) -> Dict[str, Any]:
        return await self._c._request("GET", "/v1/webhook-secret")

    async def rotate(self) -> Dict[str, Any]:
        return await self._c._request("POST", "/v1/webhook-secret/rotate")


class _AsyncModels:
    def __init__(self, client: AsyncAIgateway) -> None:
        self._c = client

    async def list(self, *, modality: Optional[str] = None, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {k: v for k, v in {"modality": modality, "provider": provider}.items() if v}
        out = await self._c._request("GET", "/v1/models", params=params)
        return out.get("data", [])

    async def get(self, id: str) -> Dict[str, Any]:
        return await self._c._request("GET", f"/v1/models/{id}")
