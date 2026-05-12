"""
Модели для сущности «Заказ» (Order).

SQLAlchemy-модель для хранения в БД и Pydantic-схемы для API.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ───────────────────────────── Статусы заказа ─────────────────────────────

class OrderStatus(str, PyEnum):
    """Возможные статусы заказа."""

    PENDING = "pending"          # Ожидает подтверждения
    CONFIRMED = "confirmed"      # Подтверждён
    SHIPPED = "shipped"          # Отправлен
    DELIVERED = "delivered"      # Доставлен
    CANCELLED = "cancelled"      # Отменён


# ───────────────────────────── SQLAlchemy ORM ─────────────────────────────

class OrderORM(Base):
    """ORM-модель заказа. Хранится в таблице orders."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, comment="ID товара"
    )
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False, comment="ID продавца"
    )
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Имя покупателя")
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, comment="Количество единиц")
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="Общая стоимость")
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, comment="Статус заказа"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Дата создания"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Дата обновления"
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, status='{self.status}', total={self.total_price})>"


# ───────────────────────────── Pydantic схемы ─────────────────────────────

class OrderBase(BaseModel):
    """Общие поля заказа."""

    buyer_name: str = Field(
        default="",
        min_length=0,
        max_length=255,
        description="Имя покупателя (игнорируется, устанавливается из JWT)",
    )
    quantity: int = Field(..., gt=0, description="Количество единиц товара")


class OrderCreate(OrderBase):
    """Схема создания нового заказа."""

    product_id: int = Field(..., gt=0, description="ID товара")
    seller_id: int = Field(..., gt=0, description="ID продавца")


class OrderUpdate(BaseModel):
    """Схема обновления статуса заказа."""

    status: OrderStatus = Field(..., description="Новый статус заказа")


class OrderResponse(OrderBase):
    """Схема ответа — полная информация о заказе."""

    id: int
    product_id: int
    seller_id: int
    total_price: Decimal
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
