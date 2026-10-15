"""Dedicated RQ consumer (profile: queue). Consumes the 'weather' queue."""
import logging

import redis
from rq import Queue, Worker

from app.config import settings
from app.logging_config import configure_logging

log = logging.getLogger("queue-worker")


def main() -> None:
    configure_logging()
    conn = redis.from_url(settings.redis_url)
    worker = Worker([Queue("weather", connection=conn)], connection=conn)
    log.info("consuming 'weather' queue")
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
