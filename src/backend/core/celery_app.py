import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    backend=redis_url,
    broker=redis_url
)

celery_app.conf.task_routes = {"src.backend.api.v1.auth.*": "main-queue"}
celery_app.conf.update(task_track_started=True)