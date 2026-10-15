"""Structured JSON logging so Promtail/Loki can parse request logs."""
import logging
import sys

from pythonjsonlogger import jsonlogger

from .config import settings


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
    )
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    # Quiet the noisy access logger; uvicorn access logs are emitted separately.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
