import pytest
from sqlalchemy.future import select

from app.models.models import CategoryRule, Transaction
from app.services.worker import process_csv_job


# Helper context manager for session injection
# This mimics the behavior of the ARQ worker session context.
class _Ctx:
    def __init__(self, sess):
        self.sess = sess

    async def __aenter__(self):
        # Returns the actual AsyncSession instance
        return self.sess

    async def __aexit__(self, exc_type, exc, tb):
        # Does nothing, as the test fixture manages the session lifecycle
        pass


@pytest.mark.asyncio
async def test_process_csv_job_with_rules(async_session, monkeypatch, test_user):
    """
    Ensures that:
      - CSV rows are processed
      - rules are applied (lowercased keyword matching)
      - AI prediction is skipped when rule matches
      - transactions are created correctly
    """

    # ---------------------------------------------------------
    # 1. Insert a rule for the user
    # ---------------------------------------------------------
    rule = CategoryRule(
        user_id=test_user["id"], keyword="amazon", category="Shopping"  # lowercase rule
    )
    async_session.add(rule)
    await async_session.commit()

    # ---------------------------------------------------------
    # 2. Fake CSV rows (what upload endpoint supplies)
    # ---------------------------------------------------------
    raw_rows = [
        {
            "Date": "2025-10-01",
            "Description": "AMAZON PURCHASE 1234",
            "Amount": "45.50",
        },
        {
            "Date": "2025-10-02",
            "Description": "Some Unknown Merchant",
            "Amount": "19.99",
        },
    ]

    # ---------------------------------------------------------
    # 3. Mock AI category prediction for unknown merchant
    # ---------------------------------------------------------
    async def fake_predict(text):
        return "AI_Category"

    monkeypatch.setattr("app.services.worker.predict_category", fake_predict)

    # ---------------------------------------------------------
    # 4. Run worker job (using injected session factory)
    # ---------------------------------------------------------
    class DummyCtx:  # ARQ normally passes this
        pass

    # Inject the test session via a factory returning our context manager.
    def session_factory():
        return _Ctx(async_session)

    # Run worker job using injected session factory. Session factory is passed
    # as a separate argument for readability and line-length compliance.
    result = await process_csv_job(
        DummyCtx(),
        str(test_user["id"]),
        raw_rows,
        session_factory=session_factory,
    )
    assert result is True

    # ---------------------------------------------------------
    # 5. Validate stored transactions
    # ---------------------------------------------------------
    tx_query = await async_session.execute(
        select(Transaction).where(Transaction.user_id == test_user["id"])
    )
    transactions = tx_query.scalars().all()

    assert len(transactions) == 2

    # First transaction should match deterministic rule "amazon"
    t1 = transactions[0]
    assert t1.category == "Shopping"

    # Second should use mocked AI category
    t2 = transactions[1]
    assert t2.category == "AI_Category"


@pytest.mark.asyncio
async def test_process_csv_job_sanitization(async_session, monkeypatch, test_user):
    """
    Ensures sanitize_description masks PII before saving.
    """

    raw_rows = [
        {
            "Date": "2025-10-03",
            "Description": "PAYMENT TO 12345678901",
            "Amount": "100.00",
        },
    ]

    # mock AI since we don't depend on real HTTP
    async def fake_predict(text):
        return "Utilities"

    monkeypatch.setattr("app.services.worker.predict_category", fake_predict)

    # Inject test session via a lambda factory returning our context manager.
    class DummyCtx:
        pass

    def session_factory():
        return _Ctx(async_session)

    # Invoke worker with the injected session factory. Keep args on separate
    # lines to stay within the project's 88-char limit.
    await process_csv_job(
        DummyCtx(),
        str(test_user["id"]),
        raw_rows,
        session_factory=session_factory,
    )

    # fetch transactions
    tx_query = await async_session.execute(
        select(Transaction).where(Transaction.user_id == test_user["id"])
    )
    tx = tx_query.scalars().first()

    # ensure PII was masked by sanitize_description
    assert "[REDACTED]" in tx.clean_description
    assert "12345678901" not in tx.clean_description
