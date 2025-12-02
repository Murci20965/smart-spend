# app/routers/transactions.py

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
# (no longer using sqlalchemy.update here)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import CategoryRule, Transaction
from app.schemas.schemas import (
    AdviceRequest,
    AdviceResponse,
    CategorySpend,
    DashboardSummary,
    MonthlySpend,
    TransactionCorrection,
    TransactionOut,
)
from app.services.ai_service import generate_spending_advice

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# ============================================================
# LIST TRANSACTIONS (paginated)
# ============================================================
@router.get("/", response_model=list[TransactionOut])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(q)
    txs = result.scalars().all()
    return txs


# ============================================================
# GET SINGLE TRANSACTION
# ============================================================
@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(Transaction).where(
        Transaction.id == transaction_id, Transaction.user_id == current_user.id
    )
    result = await db.execute(q)
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return tx


# ============================================================
# CORRECT CATEGORY (Feedback Loop -> Create or Overwrite Rule)
# ============================================================
@router.patch("/{transaction_id}/correct")
async def correct_category(
    transaction_id: UUID,
    correction: TransactionCorrection,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Fetch transaction and validate ownership
    q = select(Transaction).where(
        Transaction.id == transaction_id, Transaction.user_id == current_user.id
    )
    result = await db.execute(q)
    tx = result.scalar_one_or_none()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Build normalized keyword from cleaned description (fallback to original)
    raw_keyword = (tx.clean_description or tx.original_description or "").strip()
    if not raw_keyword:
        raise HTTPException(
            status_code=400,
            detail="Transaction has no usable description for rule creation.",
        )

    keyword = raw_keyword.lower()

    # Check for an existing rule (exact keyword match)
    existing_q = select(CategoryRule).where(
        CategoryRule.user_id == current_user.id, CategoryRule.keyword == keyword
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()

    if existing:
        # Overwrite existing rule's category
        existing.category = correction.correct_category
        db.add(existing)  # mark as dirty / updated
    else:
        # Create new rule (store keyword normalized)
        new_rule = CategoryRule(
            user_id=current_user.id,
            keyword=keyword,
            category=correction.correct_category,
        )
        db.add(new_rule)

    # Update transaction record
    tx.category = correction.correct_category
    tx.is_reviewed = True

    await db.commit()
    await db.refresh(tx)

    return {"message": "Category updated and rule learned.", "transaction": tx}


# ============================================================
# DASHBOARD SUMMARY (total, top categories, monthly)
# ============================================================
@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    month: str | None = Query(None, description="Format: YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Base filter by user
    base_q = select(Transaction).where(Transaction.user_id == current_user.id)

    # Apply month filter (if provided)
    if month:
        try:
            month_start = datetime.strptime(month + "-01", "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400, detail="Invalid month format. Use YYYY-MM."
            )
        # compute next month
        if month_start.month == 12:
            next_month = datetime(month_start.year + 1, 1, 1)
        else:
            next_month = datetime(month_start.year, month_start.month + 1, 1)

        base_q = base_q.where(
            Transaction.date >= month_start, Transaction.date < next_month
        )

    result = await db.execute(base_q)
    txs = result.scalars().all()

    total_spent = sum((t.amount or 0.0) for t in txs)

    # category breakdown
    cat_map: dict[str, float] = {}
    for t in txs:
        if t.category:
            cat_map[t.category] = cat_map.get(t.category, 0.0) + (t.amount or 0.0)

    top_categories = [
        CategorySpend(category=k, total_amount=v) for k, v in cat_map.items()
    ]

    # monthly spend (aggregate by YYYY-MM)
    month_map: dict[str, float] = {}
    for t in txs:
        key = t.date.strftime("%Y-%m")
        month_map[key] = month_map.get(key, 0.0) + (t.amount or 0.0)

    monthly_spend = [
        MonthlySpend(month=k, total_amount=v) for k, v in month_map.items()
    ]

    return DashboardSummary(
        total_spent=total_spent,
        top_categories=top_categories,
        monthly_spend=monthly_spend,
    )


# ============================================================
# AI COACH — produce compact advice
# ============================================================
@router.post("/coach/advice", response_model=AdviceResponse)
async def coach_advice(
    request: AdviceRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Validate month format
    try:
        month_start = datetime.strptime(request.month + "-01", "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid month format. Use YYYY-MM."
        )

    if month_start.month == 12:
        next_month = datetime(month_start.year + 1, 1, 1)
    else:
        next_month = datetime(month_start.year, month_start.month + 1, 1)

    q = select(Transaction).where(
        Transaction.user_id == current_user.id,
        Transaction.date >= month_start,
        Transaction.date < next_month,
    )

    result = await db.execute(q)
    txs = result.scalars().all()
    total_spent = sum((t.amount or 0.0) for t in txs)

    # Call the AI helper (exists in ai_service)
    result = await generate_spending_advice(
        month=request.month, spent=total_spent, budget=request.budget_goal
    )

    # Backwards-compatible handling: generate_spending_advice historically returned
    # either a string (advice_text) or a tuple (advice_text, source). Accept both.
    if isinstance(result, tuple) and len(result) == 2:
        advice_text, source = result
    else:
        advice_text = result
        source = "ai"

    return AdviceResponse(month=request.month, advice=advice_text, source=source)
