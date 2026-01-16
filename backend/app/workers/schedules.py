"""
Celery Beat scheduled tasks configuration.
"""

from celery.schedules import crontab

from app.workers.celery_app import celery_app

# Scheduled tasks
celery_app.conf.beat_schedule = {
    # Sync quotes - morning (10:30 BRT)
    "sync-quotes-morning": {
        "task": "app.workers.tasks.quote_sync.sync_all_quotes",
        "schedule": crontab(hour=10, minute=30),
    },
    # Sync quotes - afternoon (14:00 BRT)
    "sync-quotes-afternoon": {
        "task": "app.workers.tasks.quote_sync.sync_all_quotes",
        "schedule": crontab(hour=14, minute=0),
    },
    # Sync quotes - market close (18:30 BRT)
    "sync-quotes-close": {
        "task": "app.workers.tasks.quote_sync.sync_all_quotes",
        "schedule": crontab(hour=18, minute=30),
    },
    # Calculate daily NAV (19:00 BRT)
    "calculate-daily-nav": {
        "task": "app.workers.tasks.nav_calculator.calculate_nav",
        "schedule": crontab(hour=19, minute=0),
    },
    # Generate daily snapshot (19:30 BRT)
    "generate-daily-snapshot": {
        "task": "app.workers.tasks.snapshot_generator.generate_snapshot",
        "schedule": crontab(hour=19, minute=30),
    },
    # Sync exchange rates (18:00 BRT)
    "sync-exchange-rates": {
        "task": "app.workers.tasks.quote_sync.sync_exchange_rates",
        "schedule": crontab(hour=18, minute=0),
    },
}
