# tests/unit/test_upload.py
import pytest

import app.routers.upload as upload_module
from tests.utils import csv_bytes_from_rows


@pytest.mark.asyncio
async def test_upload_success(client, auth_token, monkeypatch):
    # Fake create_pool => return fake redis with enqueue_job
    class FakeRedis:
        def __init__(self):
            self.last_job = None

        async def enqueue_job(self, func_name, user_id, transactions):
            self.last_job = {
                "func": func_name,
                "user_id": user_id,
                "transactions": transactions,
            }

            class Job:
                def __init__(self, jid):
                    self.job_id = jid

            return Job("fake-job-123")

    async def fake_create_pool(settings_arg):
        return FakeRedis()

    # Patch arq.create_pool used by upload.get_redis_pool (upload.py calls create_pool)
    monkeypatch.setattr(upload_module, "create_pool", fake_create_pool)

    rows = [
        {"date": "2025-10-01", "description": "AMAZON.COM P012", "amount": "45.50"},
        {
            "date": "2025-10-02",
            "description": "UBER TRIP TO AIRPORT",
            "amount": "25.00",
        },
    ]
    data = csv_bytes_from_rows(rows)
    files = {"file": ("test.csv", data, "text/csv")}
    headers = {"Authorization": f"Bearer {auth_token}"}

    r = await client.post("/upload/", files=files, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body
    assert body["status"] == "processing_started"


@pytest.mark.asyncio
async def test_upload_invalid_columns(client, auth_token, monkeypatch):
    # Patch create_pool to ensure it's NOT called
    async def fake_create_pool(settings_arg):
        raise AssertionError("create_pool should not be called for invalid CSV")

    monkeypatch.setattr("app.routers.upload.create_pool", fake_create_pool)

    rows = [{"bad": "x"}]
    data = csv_bytes_from_rows(rows)
    files = {"file": ("bad.csv", data, "text/csv")}
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/upload/", files=files, headers=headers)
    assert r.status_code == 400
    assert "Invalid CSV format" in r.json()["detail"]


@pytest.mark.asyncio
async def test_upload_non_csv(client, auth_token):
    files = {"file": ("not.txt", b"hello", "text/plain")}
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/upload/", files=files, headers=headers)
    assert r.status_code == 400
    assert "Only CSV files are supported" in r.json()["detail"]
