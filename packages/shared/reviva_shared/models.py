from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Column, Field, JSON, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: str = Field(index=True)
    razorpay_payment_id: str = Field(index=True)
    razorpay_order_id: Optional[str] = None
    event_type: str
    amount_paise: int = 0
    currency: str = "INR"
    customer_ref: str = Field(default="anon", index=True)
    customer_email: Optional[str] = None
    error_code: Optional[str] = None
    error_reason: Optional[str] = None
    error_description: Optional[str] = None
    error_source: Optional[str] = None
    error_step: Optional[str] = None
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    source: str = "webhook"
    created_at: datetime = Field(default_factory=utcnow)


class Diagnosis(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(index=True)
    root_cause: str
    retry_class: str
    confidence: float = 1.0
    decision_source: str
    reasoning: str = ""
    ground_truth: Optional[str] = None
    created_at: datetime = Field(default_factory=utcnow)


class RecoveryAction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(index=True)
    diagnosis_id: Optional[int] = None
    action_type: str
    status: str
    block_reason: Optional[str] = None
    razorpay_ref: Optional[str] = None
    amount_paise: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: Optional[int] = Field(default=None, index=True)
    action_id: Optional[int] = None
    actor: str = "agent"
    action: str
    decision_source: str = ""
    reason: str = ""
    amount_paise: int = 0
    outcome: str = ""
    extra: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utcnow)


class Recovery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: int = Field(index=True)
    action_id: Optional[int] = None
    amount_paise: int = 0
    recovered: bool = False
    mode: str = "sim"
    created_at: datetime = Field(default_factory=utcnow)


class MerchantState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    merchant_id: str = Field(unique=True, index=True)
    kill_switch: bool = False
    updated_at: datetime = Field(default_factory=utcnow)
