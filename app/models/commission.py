"""
Модели для сущности «Комиссия» (Commission).

SQLAlchemy-модель для хранения в БД и Pydantic-схемы для API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ───────────────────────────── SQLAlchemy ORM ─────────────────────────────

class CommissionORM(Base):
    """ORM-модель комиссии. Хранится в таблице commissions."""

    __tablename__ = "commissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, comment="ID заказа"
    )
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, comment="ID продавца"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="Сумма комиссии")
    percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, comment="Процент комиссии")
    status: Mapped[str] = mapped_column(String(50), default="pending", comment="Статус (pending / paid / refunded)")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Дата начисления"
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Дата выплаты"
    )

    def __repr__(self) -> str:
        return f"<Commission(id={self.id}, amount={self.amount}, status='{self.status}')>"


# ───────────────────────────── Pydantic схемы ─────────────────────────────

class CommissionBase(BaseModel):
    """Общие поля комиссии."""

    amount: Decimal = Field(..., gt=0, decimal_places=2, description="Сумма комиссии")
    percentage: Decimal = Field(..., gt=0, le=100, decimal_places=2, description="Процент комиссии")
    status: str = Field(default="pending", pattern=r"^(pending|paid|refunded)$", description="Статус")


class CommissionCreate(CommissionBase):
    """Схема создания новой комиссии."""

    order_id: int = Field(..., gt=0, description="ID заказа")
    seller_id: int = Field(..., gt=0, description="ID продавца")


class CommissionUpdate(BaseModel):
    """Схема обновления статуса комиссии."""

    status: str = Field(..., pattern=r"^(pending|paid|refunded)$", description="Новый статус")
    paid_at: Optional[datetime] = None


class CommissionResponse(CommissionBase):
    """Схема ответа — полная информация о комиссии."""

    id: int
    order_id: int
    seller_id: int
    created_at: datetime
    paid_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
