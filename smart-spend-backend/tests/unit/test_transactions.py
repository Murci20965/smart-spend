import pytest
from httpx import AsyncClient
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_transactions_flow(
    client: AsyncClient,
    async_session,
    test_user,
    monkeypatch,
):
    # Insert some transactions directly into DB
    from app.models.models import Transaction

    rows = [
        Transaction(
            user_id=test_user["id"],
            date="2025-10-01",
            original_description="AMAZON.COM P012",
            clean_description="amazon.com p012",
            amount=45.50,
            category="Shopping",
        ),
        Transaction(
            user_id=test_user["id"],
            date="2025-10-02",
            original_description="UBER TRIP TO AIRPORT",
            clean_description="uber trip to airport",
            amount=25.00,
            category="Transport",
        ),
        Transaction(
            user_id=test_user["id"],
            date="2025-10-03",
            original_description="NETFLIX MONTHLY CHARGE",
            clean_description="netflix monthly charge",
            amount=15.99,
            category="Entertainment",
        ),
    ]
    async_session.add_all(rows)
    await async_session.commit()

    # List transactions
    headers = {"Authorization": f"Bearer {create_token_for(test_user)}"}
    r = await client.get("/transactions/", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    # Dashboard summary
    r2 = await client.get(
        "/transactions/dashboard/summary?month=2025-10", headers=headers
    )
    assert r2.status_code == 200
    summary = r2.json()
    assert "total_spent" in summary

    # Correction: create/overwrite rule
    # Pick one transaction id
    tx_id = data[0]["id"]
    payload = {"correct_category": "Groceries"}
    r3 = await client.patch(
        f"/transactions/{tx_id}/correct", json=payload, headers=headers
    )
    assert r3.status_code == 200
    res3 = r3.json()
    assert res3["message"].startswith("Category updated")

    # Advice: mock the advice generator
    async def fake_advice(*args, **kwargs):
        return "Do X, Y, Z"

    monkeypatch.setattr("app.services.ai_service.generate_spending_advice", fake_advice)
    r4 = await client.post(
        "/transactions/coach/advice",
        json={"month": "2025-10", "budget_goal": 500},
        headers=headers,
    )
    assert r4.status_code == 200
    assert "advice" in r4.json()


def create_token_for(user):
    return create_access_token({"sub": str(user["id"])})
