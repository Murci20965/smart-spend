# tests/unit/test_jobs.py
import pytest

import app.routers.jobs as jobs_module
# csv_bytes_from_rows is not needed here


@pytest.mark.asyncio
async def test_get_job_status(client, auth_token, monkeypatch):
    # Fake job object
    class FakeJob:
        def __init__(self, jid, redis):
            self._jid = jid

        async def status(self):
            return "complete"

    # Patch Job class used directly in jobs_module
    monkeypatch.setattr(jobs_module, "Job", FakeJob)

    # Patch create_pool to return a dummy pool (not used by FakeJob but required)
    async def fake_create_pool(settings_arg):
        return object()

    monkeypatch.setattr(jobs_module, "create_pool", fake_create_pool)

    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.get("/jobs/some-job-id", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["job_id"] == "some-job-id"
    assert body["status"] == "complete"
