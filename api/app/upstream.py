"""Thin async proxy to the Open-Meteo / BigDataCloud upstreams."""
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from .config import settings

_client: Optional[httpx.AsyncClient] = None


def client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=settings.upstream_timeout,
            headers={"User-Agent": "weather-bff/1.0 (+docker-compose)"},
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _get_json(url: str, params: dict[str, Any]) -> Any:
    try:
        resp = await client().get(url, params=params)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"upstream unreachable: {exc}") from exc
    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"upstream error {resp.status_code}")
    try:
        return resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="upstream returned invalid JSON") from exc


async def geocode(params: dict[str, Any]) -> Any:
    # Upstream expects name/count/language/format.
    return await _get_json(settings.upstream_geo, params)


async def weather(params: dict[str, Any]) -> Any:
    return await _get_json(settings.upstream_weather, params)


async def air_quality(params: dict[str, Any]) -> Any:
    return await _get_json(settings.upstream_aqi, params)


async def reverse(params: dict[str, Any]) -> Any:
    return await _get_json(settings.upstream_reverse, params)
