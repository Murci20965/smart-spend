from app.core.config import settings
from app.services.worker import process_csv_job


class WorkerSettings:
    # Use the RedisSettings object directly
    redis_settings = settings.REDIS_SETTINGS

    # List of functions this worker can run
    functions = [process_csv_job]

    max_jobs = 5  # optional
