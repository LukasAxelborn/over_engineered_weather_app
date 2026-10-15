"""Enqueue a pre-warm job onto the RQ 'weather' queue.

Used by the ops cron (Ofelia) profile to demonstrate the queue pipeline.
"""
import logging

import redis
from rq import Queue

from app.config import settings
from app.logging_config import configure_logging

log = logging.getLogger("producer")


def main() -> None:
    configure_logging()
    conn = redis.from_url(settings.redis_url)
    q = Queue("weather", connection=conn)
    job = q.enqueue("worker.common.prewarm_sync")
    log.info("enqueued prewarm job %s", job.id)


if __name__ == "__main__":
    main()
