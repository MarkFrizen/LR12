"""
Модели для сущности «Продавец» (Seller).

SQLAlchemy-модель для хранения в БД и Pydantic-схемы для API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ───────────────────────────── SQLAlchemy ORM ─────────────────────────────

class SellerORM(Base):
    """ORM-модель продавца. Хранится в таблице sellers."""

    __tablename__ = "sellers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Наименование продавца")
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="Email продавца")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="Телефон")
    rating: Mapped[float] = mapped_column(Float, default=0.0, comment="Рейтинг (0–5)")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Дата регистрации"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Дата последнего обновления"
    )

    def __repr__(self) -> str:
        return f"<Seller(id={self.id}, name='{self.name}', email='{self.email}')>"


# ───────────────────────────── Pydantic схемы ─────────────────────────────

class SellerBase(BaseModel):
    """Общие поля продавца, используемые при создании и возврате."""

    name: str = Field(..., min_length=1, max_length=255, description="Наименование продавца")
    email: EmailStr = Field(..., description="Email продавца")
    phone: Optional[str] = Field(None, max_length=20, description="Номер телефона")
    rating: float = Field(default=0.0, ge=0.0, le=5.0, description="Рейтинг (0–5)")


class SellerCreate(SellerBase):
    """Схема для создания нового продавца (POST-запрос)."""
    pass


class SellerUpdate(BaseModel):
    """Схема для частичного обновления продавца (PATCH-запрос).
    rating исключён — пересчитывается автоматически из отзывов.
    """

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)


class SellerResponse(SellerBase):
    """Схема ответа — полная информация о продавце."""

    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
