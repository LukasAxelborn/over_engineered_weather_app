"""Shared worker logic: pre-warm popular cities into the same Redis cache keys
the API reads from, plus a tiny health endpoint."""
import asyncio
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from app import cache, upstream
from app.config import settings
from app.keys import AQI_QUERY, WEATHER_QUERY, cache_key

log = logging.getLogger("worker")

FALLBACK_CITIES = ["Stockholm", "London", "New York", "Tokyo", "Paris", "Berlin", "Sydney"]

state = {"last_run": None, "last_count": 0}


def cities() -> list[str]:
    raw = os.getenv("WORKER_CITIES", "")
    parsed = [c.strip() for c in raw.split(",") if c.strip()]
    return parsed or FALLBACK_CITIES


async def _prewarm_one(city: str) -> int:
    geo_params = {"name": city, "count": "1", "language": "en", "format": "json"}
    gkey = cache_key("geocode", geo_params)
    geo = await cache.get_json(gkey)
    if geo is None:
        geo = await upstream.geocode(geo_params)
        await cache.set_json(gkey, geo, settings.ttl_geo)

    results = (geo or {}).get("results") or []
    if not results:
        log.info("prewarm: no geocode result for %s", city)
        return 0
    loc = results[0]
    lat, lon = str(loc["latitude"]), str(loc["longitude"])

    wx_params = dict(WEATHER_QUERY, latitude=lat, longitude=lon)
    wkey = cache_key("weather", wx_params)
    if await cache.get_json(wkey) is None:
        await cache.set_json(wkey, await upstream.weather(wx_params), settings.ttl_weather)

    aq_params = dict(AQI_QUERY, latitude=lat, longitude=lon)
    akey = cache_key("air-quality", aq_params)
    if await cache.get_json(akey) is None:
        await cache.set_json(akey, await upstream.air_quality(aq_params), settings.ttl_aqi)

    log.info("prewarm: cached %s", city)
    return 1


async def prewarm_all() -> int:
    count = 0
    for city in cities():
        try:
            count += await _prewarm_one(city)
        except Exception as exc:  # one bad city shouldn't abort the batch
            log.warning("prewarm failed for %s: %s", city, exc)
    log.info("prewarm complete: %d cities", count)
    return count


def prewarm_sync() -> int:
    """Runnable by APScheduler and by an RQ worker."""
    count = asyncio.run(prewarm_all())
    state["last_run"] = time.time()
    state["last_count"] = count
    return count


class _Health(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path not in ("/health", "/healthz", "/"):
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps({
            "status": "ok",
            "last_run": state["last_run"],
            "last_count": state["last_count"],
            "cities": cities(),
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silence default stderr logging
        return


def start_health_server(port: int = 9000) -> None:
    server = ThreadingHTTPServer(("0.0.0.0", port), _Health)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("worker health server on :%d", port)
