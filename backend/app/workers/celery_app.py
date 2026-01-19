"""
Celery application configuration.
"""

from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_init

from app.config import settings
from app.core.logging import setup_logging


@worker_init.connect
def init_worker(**kwargs):
    """Initialize logging when Celery worker starts."""
    setup_logging()


def get_redis_url(db: int = 0) -> str:
    """Get Redis URL with optional database number."""
    if settings.redis_url:
        base_url = str(settings.redis_url).rstrip("/")
        # Replace db number if present, otherwise append
        if base_url.count("/") >= 3:
            parts = base_url.rsplit("/", 1)
            return f"{parts[0]}/{db}"
        return f"{base_url}/{db}"
    return f"redis://localhost:6379/{db}"


# Create Celery app
celery_app = Celery(
    "investctr",
    broker=settings.celery_broker_url or get_redis_url(1),
    backend=settings.celery_result_backend or get_redis_url(2),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes
    task_soft_time_limit=300,  # 5 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.workers.tasks"])

# Beat schedule for periodic tasks
# Times are configured in BRT (America/Sao_Paulo timezone, configured above)
celery_app.conf.beat_schedule = {
    # Sync quotes 3x daily: 10:30, 14:00, 18:30 BRT
    "sync-quotes-morning": {
        "task": "sync_all_quotes",
        "schedule": crontab(hour=10, minute=30),
        "options": {"queue": "default"},
    },
    "sync-quotes-afternoon": {
        "task": "sync_all_quotes",
        "schedule": crontab(hour=14, minute=0),
        "options": {"queue": "default"},
    },
    "sync-quotes-evening": {
        "task": "sync_all_quotes",
        "schedule": crontab(hour=18, minute=30),
        "options": {"queue": "default"},
    },
    # Calculate daily NAV at 19:00 BRT (after quote sync at 18:30)
    "calculate-daily-nav": {
        "task": "calculate_daily_nav",
        "schedule": crontab(hour=19, minute=0),
        "options": {"queue": "default"},
    },
    # Generate daily portfolio snapshots at 19:30 BRT (after NAV calculation)
    "generate-daily-snapshot": {
        "task": "generate_daily_snapshot",
        "schedule": crontab(hour=19, minute=30),
        "options": {"queue": "default"},
    },
}
