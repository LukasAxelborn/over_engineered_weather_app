"""Application configuration, loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Identity
    app_name: str = "weather-bff"
    environment: str = "production"
    log_level: str = "INFO"

    # Upstreams (Open-Meteo + BigDataCloud reverse geocoder)
    upstream_geo: str = "https://geocoding-api.open-meteo.com/v1/search"
    upstream_weather: str = "https://api.open-meteo.com/v1/forecast"
    upstream_aqi: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    upstream_reverse: str = "https://api.bigdatacloud.net/data/reverse-geocode-client"
    upstream_timeout: float = 10.0

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Postgres
    database_url: str = "postgresql://weather:weather@postgres:5432/weather"

    # Cache TTLs (seconds) — mirror the client-side behaviour.
    ttl_weather: int = 3000   # 50 min
    ttl_aqi: int = 3000       # 50 min
    ttl_geo: int = 86400      # 24 h
    ttl_reverse: int = 86400  # 24 h

    # Rate limiting (per client IP): max requests per window.
    rate_limit_requests: int = 120
    rate_limit_window: int = 60

    # CORS (same-origin in production; permissive only in dev).
    cors_origins: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
