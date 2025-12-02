import asyncio
import io

import pandas as pd
from arq import create_pool
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)

from app.core.config import settings
from app.core.dependencies import get_current_user, get_redis_pool

router = APIRouter(prefix="/upload", tags=["Upload"])


@router.post("/")
async def upload_csv(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    redis_pool=Depends(get_redis_pool),
):
    """
    Upload CSV → standardize columns → validate → enqueue background job.
    """

    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported.")

    # Read CSV content
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    # --- START Best Guess Mapping Logic ---

    # 1. Standardize column names (lowercase, no leading/trailing spaces)
    df.columns = df.columns.str.strip().str.lower()

    # 2. Define acceptable alternatives for required fields
    MAPPINGS = {
        "description": [
            "payee",
            "details",
            "memo",
            "transaction_details",
            "transaction details",
        ],
        "amount": ["value", "debit", "credit", "trans_amount", "transaction amount"],
        "date": [
            "transaction_date",
            "transaction date",
            "posted_date",
            "posted date",
            "trans_date",
        ],
    }

    found_columns = {}
    missing_columns = []

    for standard_col, alternatives in MAPPINGS.items():
        # Check if the standard name or an alternative is present
        if standard_col in df.columns:
            found_columns[standard_col] = standard_col
        else:
            found_match = False
            for alt in alternatives:
                if alt in df.columns:
                    found_columns[standard_col] = alt
                    found_match = True
                    break
            if not found_match:
                missing_columns.append(standard_col)

    # 3. Raise an error if essential columns are still missing
    if missing_columns:
        # Keep detail short to avoid very long error lines
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid CSV format. Missing required columns: "
                + ", ".join(missing_columns)
            ),
        )

    # 4. Rename columns in the DataFrame to your internal standard names
    df = df.rename(columns={v: k for k, v in found_columns.items()})

    # --- END Best Guess Mapping Logic ---
    # df now has 'description', 'amount', and 'date' columns.

    # Convert rows to dict
    transactions = df.to_dict(orient="records")

    # Redis queue (use app-level pool if configured)
    redis = redis_pool

    # If the DI dependency didn't provide a pool (common in tests), the
    # app-level pool will be skipped. Allow tests to monkeypatch a module-
    # level `get_redis_pool` on `app.routers.upload` and call it if present.
    if redis is None:
        try:
            from importlib import import_module

            mod = import_module("app.routers.upload")
            candidate = getattr(mod, "get_redis_pool", None)
            if callable(candidate):
                maybe = candidate()
                if asyncio.iscoroutine(maybe):
                    redis = await maybe
                else:
                    redis = maybe
        except Exception:
            redis = None

        # Fallback: create a pool on-demand (this allows tests to monkeypatch
        # `upload.create_pool` and also supports non-container local runs).
        if redis is None:
            try:
                redis = await create_pool(settings.REDIS_SETTINGS)
            except Exception:
                raise HTTPException(
                    status_code=503, detail="Background queue is not available"
                )

    # Enqueue ARQ job
    job = await redis.enqueue_job(
        "process_csv_job",
        current_user.id,
        transactions,
    )

    return {
        "job_id": job.job_id,
        "status": "processing_started",
        "message": "CSV uploaded and queued for processing.",
    }
