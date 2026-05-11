"""
Модели для сущности «Товар» (Product).

SQLAlchemy-модель для хранения в БД и Pydantic-схемы для API.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ───────────────────────────── SQLAlchemy ORM ─────────────────────────────

class ProductORM(Base):
    """ORM-модель товара. Хранится в таблице products."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    seller_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, comment="ID продавца"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Название товара")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Описание товара")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, comment="Цена")
    stock: Mapped[int] = mapped_column(Integer, default=0, comment="Остаток на складе")
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="Категория")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Дата добавления"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True, comment="Дата обновления"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name='{self.name}', price={self.price})>"


# ───────────────────────────── Pydantic схемы ─────────────────────────────

class ProductBase(BaseModel):
    """Общие поля товара."""

    name: str = Field(..., min_length=1, max_length=255, description="Название товара")
    description: Optional[str] = Field(None, description="Описание товара")
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Цена")
    stock: int = Field(default=0, ge=0, description="Остаток на складе")
    category: Optional[str] = Field(None, max_length=100, description="Категория")


class ProductCreate(ProductBase):
    """Схема создания нового товара."""

    seller_id: int = Field(..., gt=0, description="ID продавца")


class ProductUpdate(BaseModel):
    """Схема частичного обновления товара."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    stock: Optional[int] = Field(None, ge=0)
    category: Optional[str] = Field(None, max_length=100)
    seller_id: Optional[int] = Field(None, gt=0)


class ProductResponse(ProductBase):
    """Схема ответа — полная информация о товаре."""

    id: int
    seller_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
