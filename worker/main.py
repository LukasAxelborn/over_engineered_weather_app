"""Worker entry point.

Runs an APScheduler background scheduler that periodically pre-warms the Redis
cache for popular cities, and exposes a health endpoint on :9000.
Also runs an RQ consumer so jobs enqueued by producers are processed too.
"""
import logging
import os
import signal
import threading
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.logging_config import configure_logging
from worker.common import prewarm_sync, start_health_server

log = logging.getLogger("worker")


def _run_rq() -> None:
    """Best-effort RQ consumer; failure must not take the scheduler down."""
    try:
        import redis
        from rq import Queue, Worker

        conn = redis.from_url(settings.redis_url)
        worker = Worker([Queue("weather", connection=conn)], connection=conn)
        log.info("rq consumer started on queue 'weather'")
        worker.work(with_scheduler=False)
    except Exception as exc:
        log.warning("rq consumer disabled: %s", exc)


def main() -> None:
    configure_logging()
    interval = int(os.getenv("WORKER_INTERVAL_SEC", "3600"))
    health_port = int(os.getenv("WORKER_HEALTH_PORT", "9000"))
    log.info("starting worker (interval=%ss)", interval)

    try:
        prewarm_sync()  # initial warm-up
    except Exception as exc:
        log.warning("initial prewarm failed (upstream may be down): %s", exc)

    scheduler = BackgroundScheduler()
    scheduler.add_job(prewarm_sync, "interval", seconds=interval, id="prewarm",
                      max_instances=1, coalesce=True)
    scheduler.start()

    threading.Thread(target=_run_rq, daemon=True).start()
    start_health_server(health_port)

    stop = threading.Event()

    def _shutdown(signum, _frame):
        log.info("received signal %s, shutting down", signum)
        scheduler.shutdown(wait=False)
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    stop.wait()


if __name__ == "__main__":
    main()
