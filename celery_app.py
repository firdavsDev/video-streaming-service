import logging

from celery import Celery

from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "video_streaming",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.video_tasks"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task routing
    task_routes={
        "app.tasks.video_tasks.process_video": {"queue": "video_processing"},
        "app.tasks.video_tasks.cleanup_temp_files": {"queue": "cleanup"},
    },
    # Task settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_track_started=True,
    # Retry settings
    task_annotations={
        "app.tasks.video_tasks.process_video": {
            "rate_limit": "5/m",
            "max_retries": 3,
            "default_retry_delay": 60,
        }
    },
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-temp-files": {
            "task": "app.tasks.video_tasks.cleanup_temp_files",
            "schedule": 3600.0,  # Every hour
        },
    },
)

if __name__ == "__main__":
    celery_app.start()
