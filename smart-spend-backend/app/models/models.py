# app/models/models.py

import datetime
import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ============================================================
# USER MODEL
# ============================================================


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


# ============================================================
# CATEGORY RULE MODEL
# ============================================================


class CategoryRule(Base):
    __tablename__ = "categorization_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    keyword = Column(String(255), nullable=False)  # e.g. "NETFLIX"
    category = Column(String(255), nullable=False)  # e.g. "Entertainment"

    __table_args__ = (UniqueConstraint("user_id", "keyword", name="uq_user_keyword"),)


# ============================================================
# TRANSACTION MODEL
# ============================================================


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True, nullable=False
    )

    date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    original_description = Column(String(500))
    clean_description = Column(String(500))

    amount = Column(Float, nullable=False)
    category = Column(String(255), index=True)

    is_reviewed = Column(Boolean, default=False)

    def __init__(self, *args, date=None, **kwargs):
        """
        Ensure date strings are coerced to datetime objects so SQLite/SQLAlchemy
        DateTime columns accept them during tests and inserts.
        """
        # If a date was passed positionally via kwargs or as the date kwarg
        if date is None:
            date = kwargs.get("date")

        if isinstance(date, str):
            try:
                # Try ISO date (YYYY-MM-DD)
                d = datetime.date.fromisoformat(date)
                date = datetime.datetime(d.year, d.month, d.day)
            except Exception:
                try:
                    # Try full datetime string
                    date = datetime.datetime.fromisoformat(date)
                except Exception:
                    # If parsing fails, leave as-is and let DB raise an error
                    date = date

        if date is not None:
            kwargs["date"] = date

        super().__init__(*args, **kwargs)
