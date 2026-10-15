"""Custom Prometheus metrics for the weather BFF."""
from prometheus_client import Counter

cache_events = Counter(
    "weather_cache_events_total",
    "Cache lookups by name and result.",
    ["name", "result"],
)

upstream_requests = Counter(
    "weather_upstream_requests_total",
    "Outbound upstream proxy requests.",
    ["upstream", "status"],
)

favorite_ops = Counter(
    "weather_favorite_ops_total",
    "Favorites operations.",
    ["op"],
)
