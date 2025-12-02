from datetime import date  # Keep this import to fix date type issues

import pytest
from sqlalchemy.future import select

from app.models.models import CategoryRule


@pytest.mark.asyncio
async def test_overwrite_existing_rule(client, async_session, test_user, auth_token):
    """
    Ensure that PATCH /transactions/{id}/correct overwrites existing rule's category
    when the normalized keyword already exists.
    """

    from app.models.models import Transaction

    # 1️⃣ Create a transaction to correct later
    tx = Transaction(
        user_id=test_user["id"],
        date=date(2025, 10, 1),  # Use datetime.date object
        original_description="NETFLIX MONTHLY CHARGE",
        clean_description="netflix monthly charge",
        amount=15.99,
        category="Entertainment",
    )
    async_session.add(tx)
    try:
        await async_session.commit()
    except Exception:
        await async_session.rollback()
        raise
    await async_session.refresh(tx)

    # 2️⃣ Create an existing rule with the same normalized keyword
    rule = CategoryRule(
        user_id=test_user["id"],
        keyword="netflix monthly charge",
        category="OldCategory",
    )
    async_session.add(rule)
    try:
        await async_session.commit()
    except Exception:
        await async_session.rollback()
        raise
    # No need to refresh the rule to avoid concurrency conflicts

    # 3️⃣ Call the correction endpoint to set new category
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {"correct_category": "Groceries"}
    r = await client.patch(
        f"/transactions/{tx.id}/correct", json=payload, headers=headers
    )
    assert r.status_code == 200
    body = r.json()
    assert "Category updated" in body["message"]

    # 4️⃣ Verify the rule was updated (overwrite)
    q = await async_session.execute(
        select(CategoryRule).where(
            CategoryRule.user_id == test_user["id"],
            CategoryRule.keyword == "netflix monthly charge",
        )
    )
    updated_rule = q.scalars().first()
    assert updated_rule is not None
    assert updated_rule.category == "Groceries"

    # 5️⃣ Verify transaction was updated and flagged reviewed
    tx_q = await async_session.execute(
        select(Transaction).where(Transaction.id == tx.id)
    )
    updated_tx = tx_q.scalars().first()
    assert updated_tx.category == "Groceries"
    assert updated_tx.is_reviewed is True


@pytest.mark.asyncio
async def test_create_new_rule_when_not_exists(
    client, async_session, test_user, auth_token
):
    """
    If no rule exists, correction should create a new rule
    (with normalized keyword lowercase).
    """

    from app.models.models import Transaction

    # 1️⃣ Create a transaction with no category
    tx = Transaction(
        user_id=test_user["id"],
        date=date(2025, 10, 2),  # Use datetime.date object
        original_description="UBER TRIP TO AIRPORT",
        clean_description="uber trip to airport",
        amount=25.0,
        category=None,
    )
    async_session.add(tx)
    try:
        await async_session.commit()
    except Exception:
        await async_session.rollback()
        raise
    await async_session.refresh(tx)

    # 2️⃣ Call the correction endpoint to set new category
    headers = {"Authorization": f"Bearer {auth_token}"}
    payload = {"correct_category": "Transport"}
    r = await client.patch(
        f"/transactions/{tx.id}/correct", json=payload, headers=headers
    )
    assert r.status_code == 200

    # 3️⃣ Verify new rule exists and is lowercased
    q = await async_session.execute(
        select(CategoryRule).where(
            CategoryRule.user_id == test_user["id"],
            CategoryRule.keyword == "uber trip to airport",
        )
    )
    new_rule = q.scalars().first()
    assert new_rule is not None
    assert new_rule.category == "Transport"
