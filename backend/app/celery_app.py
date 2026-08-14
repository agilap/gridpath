from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery("gridpath")

celery_app.conf.update(
    # -- Broker ----------------------------------------------------
    broker_url=settings.UPSTASH_REDIS_URL,
    broker_use_ssl={
        "ssl_cert_reqs": "none",
    },

    # -- Result backend --------------------------------------------
    result_backend=settings.UPSTASH_REDIS_URL,
    redis_backend_use_ssl={
        "ssl_cert_reqs": "none",
    },

    # -- Serialization ---------------------------------------------
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # -- Result lifecycle ------------------------------------------
    result_expires=86400,
    task_time_limit=300,
    task_soft_time_limit=270,
    task_ignore_result=False,
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # -- Workers ---------------------------------------------------
    include=["app.tasks.analyze"],
    worker_concurrency=settings.CELERY_CONCURRENCY,
)
