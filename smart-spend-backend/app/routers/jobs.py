from arq import create_pool
from arq.jobs import Job
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.dependencies import get_current_user, get_redis_pool

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}")
async def get_job_status(
    job_id: str,
    current_user=Depends(get_current_user),
    redis_pool=Depends(get_redis_pool),
):
    """
    Allows the logged-in user to check the status of their job.
    """
    redis = redis_pool
    if redis is None:
        try:
            redis = await create_pool(settings.REDIS_SETTINGS)
        except Exception:
            raise HTTPException(
                status_code=503, detail="Background queue is not available"
            )

    job = Job(job_id, redis)
    status = await job.status()

    return {"job_id": job_id, "status": status}
