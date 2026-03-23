from __future__ import annotations

from typing import Any, Dict
from celery import Celery

from app.settings import settings


class TaskPublisher:
    def __init__(self) -> None:
        self.client: Celery = Celery(broker=settings.celery_broker_url)

    def publish(
        self,
        task_name: str,
        payload: Dict[str, Any],
    ) -> None:
        self.client.send_task(task_name, args=[payload])
