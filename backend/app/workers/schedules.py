"""
Celery Beat scheduled tasks configuration.
"""

from celery.schedules import crontab

from app.workers.celery_app import celery_app

# Scheduled tasks
# Note: Task names must match the 'name' parameter in @celery_app.task decorator
celery_app.conf.beat_schedule = {
    # Sync quotes - morning (10:30 BRT = 13:30 UTC)
    "sync-quotes-morning": {
        "task": "sync_all_quotes",
        "schedule": crontab(hour=13, minute=30),
    },
    # Sync quotes - afternoon (14:00 BRT = 17:00 UTC)
    "sync-quotes-afternoon": {
        "task": "sync_all_quotes",
        "schedule": crontab(hour=17, minute=0),
    },
    # Sync quotes - market close (18:30 BRT = 21:30 UTC)
    "sync-quotes-close": {
        "task": "sync_all_quotes",
        "schedule": crontab(hour=21, minute=30),
    },
    # Calculate daily NAV (19:00 BRT = 22:00 UTC)
    "calculate-daily-nav": {
        "task": "calculate_daily_nav",
        "schedule": crontab(hour=22, minute=0),
    },
    # Generate daily snapshot (19:30 BRT = 22:30 UTC)
    "generate-daily-snapshot": {
        "task": "generate_daily_snapshot",
        "schedule": crontab(hour=22, minute=30),
    },
}
