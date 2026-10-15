"""Shared cache-key derivation (used by both the API and the worker)."""
import hashlib
import json
from typing import Any


def cache_key(name: str, params: dict[str, Any]) -> str:
    blob = json.dumps({k: params[k] for k in sorted(params)}, separators=(",", ":"))
    digest = hashlib.sha1(blob.encode()).hexdigest()[:16]
    return f"cache:{name}:{digest}"


# Exact upstream query shapes the frontend uses, so the worker pre-warms the
# very same cache entries the API will look up.
WEATHER_QUERY = {
    "current": (
        "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
        "precipitation,weather_code,surface_pressure,wind_speed_10m,"
        "wind_direction_10m,wind_gusts_10m,uv_index"
    ),
    "hourly": (
        "temperature_2m,apparent_temperature,relative_humidity_2m,"
        "precipitation_probability,precipitation,weather_code,surface_pressure,"
        "visibility,wind_speed_10m,wind_direction_10m,uv_index,is_day,dew_point_2m"
    ),
    "daily": (
        "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,"
        "apparent_temperature_min,sunrise,sunset,uv_index_max,precipitation_sum,"
        "precipitation_probability_max,wind_speed_10m_max"
    ),
    "timezone": "auto",
    "forecast_days": "7",
    "wind_speed_unit": "ms",
}

AQI_QUERY = {
    "current": "european_aqi,us_aqi,pm2_5,pm10",
    "timezone": "auto",
}
