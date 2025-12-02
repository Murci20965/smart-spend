"""ARQ worker job processor for CSV uploads.

This module implements the ARQ job that processes uploaded CSV rows and
persists transactions into the database. The tests expect a module-level
symbol named `async_session` which yields an async session context manager;
we export `AsyncSessionLocal` under that name so tests can monkeypatch it.
"""

import datetime
import logging
from uuid import UUID

from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal  # sessionmaker
from app.models.models import CategoryRule, Transaction
from app.services.ai_service import predict_category, sanitize_description

logger = logging.getLogger("smart_spend.worker")


async def process_csv_job(
    ctx, user_id: str, raw_transactions: list, session_factory=None
):
    """Process a CSV upload job.

    Args:
        ctx: ARQ job context (ignored here).
        user_id: UUID string of the user who uploaded the CSV.
        raw_transactions: list of dicts representing CSV rows.
        session_factory: optional async session factory (for tests).

    Returns:
        True on success, False on invalid input.
    """
    # Default to the module-level `async_session` symbol so tests can
    # monkeypatch `app.services.worker.async_session` to inject a test
    # DB session. If a session_factory is explicitly provided, use that.
    session_factory = session_factory or async_session

    # Accept both UUID objects and string UUIDs (tests pass strings)
    if isinstance(user_id, UUID):
        user_uuid = user_id
        logger.debug("ARQ job started for user_id (UUID): %s", user_uuid)
    else:
        try:
            user_uuid = UUID(str(user_id))
            logger.debug("ARQ job started for user_id (str): %s", user_id)
        except (ValueError, TypeError):
            logger.error("Invalid user_id format received: %s", user_id)
            return False

    async with session_factory() as db:
        result = await db.execute(
            select(CategoryRule).where(CategoryRule.user_id == user_uuid)
        )
        rules = {r.keyword.lower(): r.category for r in result.scalars().all()}

        logger.debug("Processing %s transactions.", len(raw_transactions))

        for i, tx in enumerate(raw_transactions):
            try:
                original_desc = tx.get("description") or tx.get("Description") or ""
                clean_desc = sanitize_description(original_desc)
                clean_desc_lower = clean_desc.lower()

                date_str = tx.get("date") or tx.get("Date") or None
                try:
                    if date_str:
                        date = datetime.datetime.fromisoformat(date_str)
                        if date.tzinfo is not None:
                            date = date.replace(tzinfo=None)
                    else:
                        date = datetime.datetime.utcnow()
                except (ValueError, TypeError):
                    date = datetime.datetime.utcnow()

                amount = float(tx.get("amount") or tx.get("Amount") or 0.0)

                # deterministic keyword rules
                category = None
                for keyword, saved_cat in rules.items():
                    if keyword in clean_desc_lower:
                        category = saved_cat
                        break

                if not category:
                    category = await predict_category(clean_desc)

                new_tx = Transaction(
                    user_id=user_uuid,
                    date=date,
                    original_description=original_desc,
                    clean_description=clean_desc,
                    amount=amount,
                    category=category,
                )

                db.add(new_tx)
                await db.commit()

                logger.debug(
                    "Tx %s/%s saved. Desc: '%s...', Cat: %s",
                    i + 1,
                    len(raw_transactions),
                    (original_desc or "")[:30],
                    category,
                )

            except Exception:
                logger.exception(
                    "Failed to process transaction %s. Raw data: %s", i + 1, tx
                )
                await db.rollback()
                continue

        logger.info("ARQ job finished for user %s", user_uuid)
        return True


# Export alias for tests to monkeypatch
async_session = AsyncSessionLocal
