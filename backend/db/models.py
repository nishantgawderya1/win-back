"""SQLAlchemy 2.0 async ORM models. Persistence for audit + reporting."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BatchRun(Base):
    __tablename__ = "batch_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total_records: Mapped[int] = mapped_column(Integer, default=0)
    processed: Mapped[int] = mapped_column(Integer, default=0)
    total_at_risk: Mapped[float] = mapped_column(Float, default=0.0)
    total_recovered: Mapped[float] = mapped_column(Float, default=0.0)
    recovery_rate: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String, default="running")


class PaymentRecord(Base):
    __tablename__ = "payment_records"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    amount: Mapped[float] = mapped_column(Float)
    customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    failure_type: Mapped[str | None] = mapped_column(String, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    intervention: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    customer_recovery_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    recovered: Mapped[bool] = mapped_column(Boolean, default=False)
    recovered_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    halted: Mapped[bool] = mapped_column(Boolean, default=False)
    halt_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_reasoning: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[str] = mapped_column(String, index=True)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    agent: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HaltedAction(Base):
    __tablename__ = "halted_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[str] = mapped_column(String)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    action: Mapped[str] = mapped_column(String)  # the action that was prevented
    halt_reason: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PromiseToPay(Base):
    __tablename__ = "promise_to_pay"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    payment_id: Mapped[str] = mapped_column(String)
    customer_id: Mapped[str] = mapped_column(String)
    amount: Mapped[float] = mapped_column(Float)
    promised_date: Mapped[datetime] = mapped_column(DateTime)
    fulfilled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
