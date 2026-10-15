"""Weather BFF — proxies Open-Meteo, caches in Redis, persists favorites in Postgres."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from . import cache, db, upstream
from .config import settings
from .keys import cache_key
from .logging_config import configure_logging
from .metrics import cache_events, favorite_ops, upstream_requests

log = logging.getLogger("weather-bff")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("starting %s (%s)", settings.app_name, settings.environment)
    try:
        await db.connect()
        await db.ensure_schema()
    except Exception as exc:  # DB may not be ready yet; retried on next request.
        log.warning("database not ready at startup: %s", exc)
    yield
    await upstream.close()
    await cache.close()
    await db.close()
    log.info("stopped %s", settings.app_name)


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Request metrics + /metrics endpoint.
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


def client_identity(request: Request, device_id: str | None = None) -> str:
    fwd = request.headers.get("x-forwarded-for")
    ip = fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "unknown")
    return device_id or ip


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        identity = client_identity(request)
        if not await cache.rate_limit_ok(identity):
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": str(settings.rate_limit_window)},
            )
    return await call_next(request)


async def proxy_cached(request: Request, name: str, fn, ttl: int):
    params = dict(request.query_params)
    key = cache_key(name, params)

    async def producer():
        try:
            return await fn(params)
        except HTTPException:
            upstream_requests.labels(upstream=name, status="error").inc()
            raise

    value, hit = await cache.cached_json(key, ttl, producer)
    cache_events.labels(name, "hit" if hit else "miss").inc()
    if not hit:
        upstream_requests.labels(upstream=name, status="ok").inc()
    if value is None:
        raise HTTPException(status_code=502, detail="upstream returned no data")
    return value


@app.get("/api/health")
async def health():
    redis_ok = await cache.ping()
    db_ok = await db.ping()
    healthy = redis_ok and db_ok
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={
            "status": "ok" if healthy else "degraded",
            "redis": redis_ok,
            "database": db_ok,
            "version": app.version,
        },
    )


@app.get("/api/geocode")
async def geocode(request: Request):
    return await proxy_cached(request, "geocode", upstream.geocode, settings.ttl_geo)


@app.get("/api/weather")
async def weather(request: Request):
    return await proxy_cached(request, "weather", upstream.weather, settings.ttl_weather)


@app.get("/api/air-quality")
async def air_quality(request: Request):
    return await proxy_cached(request, "air-quality", upstream.air_quality, settings.ttl_aqi)


@app.get("/api/reverse")
async def reverse(request: Request):
    return await proxy_cached(request, "reverse", upstream.reverse, settings.ttl_reverse)


# ---------------------------------------------------------------- favorites
def device_id_from(x_device_id: str | None) -> str:
    did = (x_device_id or "").strip()
    if not did or len(did) > 128:
        raise HTTPException(status_code=400, detail="missing or invalid X-Device-Id")
    return did


@app.get("/api/favorites")
async def get_favorites(x_device_id: str | None = Header(default=None)):
    did = device_id_from(x_device_id)
    try:
        return await db.list_favorites(did)
    except Exception as exc:
        log.warning("list_favorites failed: %s", exc)
        raise HTTPException(status_code=503, detail="favorites store unavailable")


@app.post("/api/favorites", status_code=201)
async def post_favorite(payload: dict, x_device_id: str | None = Header(default=None)):
    did = device_id_from(x_device_id)
    if not {"name", "latitude", "longitude"} <= payload.keys():
        raise HTTPException(status_code=422, detail="name, latitude, longitude required")
    try:
        await db.upsert_favorite(did, payload)
    except Exception as exc:
        log.warning("upsert_favorite failed: %s", exc)
        raise HTTPException(status_code=503, detail="favorites store unavailable")
    favorite_ops.labels("upsert").inc()
    return {"ok": True}


@app.delete("/api/favorites")
async def remove_favorite(id: str, x_device_id: str | None = Header(default=None)):
    did = device_id_from(x_device_id)
    try:
        await db.delete_favorite(did, id)
    except Exception as exc:
        log.warning("delete_favorite failed: %s", exc)
        raise HTTPException(status_code=503, detail="favorites store unavailable")
    favorite_ops.labels("delete").inc()
    return {"ok": True}


# ----------------------------------------------------------------- history
@app.get("/api/history")
async def get_history(x_device_id: str | None = Header(default=None)):
    did = device_id_from(x_device_id)
    try:
        return await db.list_history(did)
    except Exception as exc:
        log.warning("list_history failed: %s", exc)
        raise HTTPException(status_code=503, detail="history store unavailable")


@app.post("/api/history", status_code=201)
async def post_history(payload: dict, x_device_id: str | None = Header(default=None)):
    did = device_id_from(x_device_id)
    if not {"name", "latitude", "longitude"} <= payload.keys():
        raise HTTPException(status_code=422, detail="name, latitude, longitude required")
    try:
        await db.add_history(did, payload)
    except Exception as exc:
        log.warning("add_history failed: %s", exc)
        raise HTTPException(status_code=503, detail="history store unavailable")
    return {"ok": True}
