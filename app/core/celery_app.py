from celery import Celery
from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

# Create Celery application
celery_app = Celery(
    "admin_panel_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
)

# Scheduled tasks (beat schedule)
celery_app.conf.beat_schedule = {
    "cleanup-expired-tokens": {
        "task": "app.tasks.tasks.cleanup_expired_tokens",
        "schedule": 3600.0,  # Every hour
    },
    "generate-daily-reports": {
        "task": "app.tasks.tasks.generate_daily_reports",
        "schedule": 86400.0,  # Every day
    },
}

logger.info("Celery application configured")
