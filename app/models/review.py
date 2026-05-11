"""
Модели для сущности «Отзыв» (Review).

SQLAlchemy-модель для хранения в БД и Pydantic-схемы для API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ───────────────────────────── SQLAlchemy ORM ─────────────────────────────

class ReviewORM(Base):
    """ORM-модель отзыва. Хранится в таблице reviews."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, comment="ID товара"
    )
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, comment="ID продавца"
    )
    buyer_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Имя покупателя")
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="Оценка (1–5)")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Текст отзыва")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Дата создания"
    )

    def __repr__(self) -> str:
        return f"<Review(id={self.id}, rating={self.rating}, product_id={self.product_id})>"


# ───────────────────────────── Pydantic схемы ─────────────────────────────

class ReviewBase(BaseModel):
    """Общие поля отзыва."""

    buyer_name: str = Field(..., min_length=1, max_length=255, description="Имя покупателя")
    rating: int = Field(..., ge=1, le=5, description="Оценка от 1 до 5")
    comment: Optional[str] = Field(None, description="Текст отзыва")


class ReviewCreate(ReviewBase):
    """Схема создания нового отзыва."""

    product_id: int = Field(..., gt=0, description="ID товара")
    seller_id: int = Field(..., gt=0, description="ID продавца")


class ReviewUpdate(BaseModel):
    """Схема частичного обновления отзыва."""

    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = None


class ReviewResponse(ReviewBase):
    """Схема ответа — полная информация об отзыве."""

    id: int
    product_id: int
    seller_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
