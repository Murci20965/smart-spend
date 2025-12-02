import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic import ConfigDict

# ============================================================
# PASSWORD VALIDATION REGEX
# ============================================================

PASSWORD_PATTERN = (
    r"^(?=.*[a-z])"  # at least one lowercase
    r"(?=.*[A-Z])"  # at least one uppercase
    r"(?=.*\d)"  # at least one number
    r"(?=.*[@$!%*?&])"  # at least one special character
    r"[A-Za-z\d@$!%*?&]{8,72}$"
)


# ============================================================
# AUTH SCHEMAS
# ============================================================


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description=(
            "Password must be 8–72 characters long and include uppercase, "
            "lowercase, number, and special character."
        ),
    )

    @field_validator("password")
    def validate_password(cls, value):
        if not re.match(PASSWORD_PATTERN, value):
            raise ValueError(
                "Password must contain at least 1 uppercase, 1 lowercase,"
                " 1 number, and 1 special character (@$!%*?&)."
            )
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============================================================
# CATEGORY RULES (Used in Feedback Learning)
# ============================================================


class CategoryRuleBase(BaseModel):
    keyword: str
    category: str


class CategoryRuleCreate(CategoryRuleBase):
    pass


class CategoryRuleOut(CategoryRuleBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# TRANSACTION SCHEMAS
# ============================================================


class TransactionBase(BaseModel):
    date: datetime | None = None
    original_description: str | None = None
    clean_description: str | None = None
    amount: float
    category: str | None = None


class TransactionOut(TransactionBase):
    id: UUID
    user_id: UUID
    is_reviewed: bool
    model_config = ConfigDict(from_attributes=True)


class TransactionCorrection(BaseModel):
    """User submits corrected category for AI learning."""

    correct_category: str


# ============================================================
# DASHBOARD SUMMARY SCHEMAS
# ============================================================


class CategorySpend(BaseModel):
    category: str
    total_amount: float


class MonthlySpend(BaseModel):
    month: str
    total_amount: float


class DashboardSummary(BaseModel):
    total_spent: float
    top_categories: list[CategorySpend]
    monthly_spend: list[MonthlySpend]


# ============================================================
# AI FINANCIAL COACH (LLaMA insights)
# ============================================================


class AdviceRequest(BaseModel):
    month: str  # e.g. “2025-10”
    budget_goal: float


class AdviceResponse(BaseModel):
    month: str
    advice: str
    source: str = Field(
        ...,
        description=(
            "Source of the advice: 'ai' for AI-generated or 'rule_based' "
            "for rule-based fallback"
        ),
    )
