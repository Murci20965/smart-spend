import pytest
from sqlalchemy.future import select

from app.models.models import CategoryRule, Transaction
from app.services.worker import process_csv_job
from tests.utils import csv_bytes_from_rows


@pytest.mark.asyncio
async def test_end_to_end_upload_and_rule_learning(client, async_session, monkeypatch):
    """
    Full pipeline:
        - Register + login (via API)
        - Upload CSV (mock enqueue, capture payload)
        - Run process_csv_job manually using the enqueued payload
        - Assert transactions saved
        - Correct a transaction (creates/overwrites a rule)
        - Upload new CSV row with same description
            -> deterministic rule applies
    """

    # 1) Register user
    reg_payload = {"email": "e2euser@example.com", "password": "StrongPass1!"}
    r = await client.post("/auth/register", json=reg_payload)
    assert r.status_code in (200, 201)
    # 2) Login for token (OAuth2 form)
    r2 = await client.post(
        "/auth/login",
        data={"username": "e2euser@example.com", "password": "StrongPass1!"},
    )
    assert r2.status_code == 200
    token = r2.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3) Mock get_redis_pool to capture transactions enqueued
    enqueued = {}

    class FakeRedis:
        async def enqueue_job(self, func_name, user_id, transactions):
            enqueued["func"] = func_name
            enqueued["user_id"] = user_id
            enqueued["transactions"] = transactions

            class Job:
                def __init__(self, jid):
                    self.job_id = jid

            return Job("e2e-job-1")

    async def fake_get_pool():
        return FakeRedis()

    monkeypatch.setattr("app.routers.upload.get_redis_pool", fake_get_pool)

    # 4) Upload CSV with a single row (NETFLIX)
    rows = [
        {
            "date": "2025-10-03",
            "description": "NETFLIX MONTHLY CHARGE",
            "amount": "15.99",
        },
    ]
    data = csv_bytes_from_rows(rows)
    files = {"file": ("e2e.csv", data, "text/csv")}
    r3 = await client.post("/upload/", files=files, headers=headers)
    assert r3.status_code == 200
    assert enqueued["func"] == "process_csv_job"
    assert len(enqueued["transactions"]) == 1

    # 5) Monkeypatch worker's async_session so worker writes into test DB
    # create context manager wrapper that yields the async_session fixture
    class _Ctx:
        def __init__(self, sess):
            self.sess = sess

        async def __aenter__(self):
            return self.sess

        async def __aexit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(
        "app.services.worker.async_session",
        lambda: _Ctx(async_session),
    )

    # 6) Mock AI predict to return 'Uncategorized'.
    #    We expect deterministic assignment from rules later.
    async def fake_predict(text):
        return "Uncategorized"

    monkeypatch.setattr("app.services.worker.predict_category", fake_predict)

    # 7) Run worker on captured payload
    await process_csv_job(None, enqueued["user_id"], enqueued["transactions"])

    # 8) Verify transaction exists
    q = await async_session.execute(
        select(Transaction).where(Transaction.user_id == enqueued["user_id"])
    )
    txs = q.scalars().all()
    assert len(txs) == 1
    tx = txs[0]
    assert "NETFLIX" in tx.original_description.upper()

    # 9) Correct the category via API (this should create a rule)
    payload = {"correct_category": "Subscriptions"}
    r4 = await client.patch(
        f"/transactions/{tx.id}/correct", json=payload, headers=headers
    )
    assert r4.status_code == 200

    # Check rule created
    q2 = await async_session.execute(
        select(CategoryRule).where(CategoryRule.user_id == enqueued["user_id"])
    )
    rules = q2.scalars().all()
    assert any("netflix" in r.keyword for r in rules)

    # 10) Upload another CSV row containing the same description and process it;
    # since rule exists, worker should assign the rule category deterministically.

    rows2 = [
        {
            "date": "2025-11-01",
            "description": "NETFLIX MONTHLY CHARGE",
            "amount": "15.99",
        },
    ]
    data2 = csv_bytes_from_rows(rows2)
    files2 = {"file": ("e2e2.csv", data2, "text/csv")}
    r5 = await client.post("/upload/", files=files2, headers=headers)
    assert r5.status_code == 200
    # capture second enqueued transactions
    assert enqueued["func"] == "process_csv_job"
    # run worker on second payload
    await process_csv_job(None, enqueued["user_id"], enqueued["transactions"])

    # Verify new transaction uses rule category "Subscriptions"
    q3 = await async_session.execute(
        select(Transaction)
        .where(Transaction.user_id == enqueued["user_id"])
        .order_by(Transaction.date.desc())
    )
    all_txs = q3.scalars().all()
    # last inserted transaction should have category "Subscriptions"
    assert any(t.category == "Subscriptions" for t in all_txs)
