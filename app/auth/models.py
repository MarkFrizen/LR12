"""
Модели для сущности «Пользователь» (User).

Включает ролевую модель: admin, moderator, seller, buyer, courier, carrier.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

# ─────────────────────────── Роли ───────────────────────────

class UserRole(str, PyEnum):
    """Роли пользователей платформы."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    SELLER = "seller"
    BUYER = "buyer"
    COURIER = "courier"
    CARRIER = "carrier"


# Роли, которые могут управлять контентом
MODERATION_ROLES = {UserRole.ADMIN, UserRole.MODERATOR}

# ─────────────────────────── ORM ───────────────────────────

class UserORM(Base):
    """ORM-модель пользователя."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="Уникальное имя пользователя"
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, comment="Email пользователя"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Хэш пароля (bcrypt)"
    )
    role: Mapped[str] = mapped_column(
        String(50), default=UserRole.BUYER.value, comment="Роль пользователя"
    )
    full_name: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="Полное имя"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Телефон"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Активен ли пользователь"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), comment="Дата регистрации"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"


# ─────────────────────────── Pydantic ───────────────────────────

class UserCreate(BaseModel):
    """Схема регистрации нового пользователя."""
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = Field(default=UserRole.BUYER)
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


class UserLogin(BaseModel):
    """Схема входа в систему."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Ответ с JWT-токеном."""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Публичные данные пользователя."""
    id: int
    username: str
    email: str
    role: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Схема обновления профиля."""
    full_name: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None


class ChangePasswordRequest(BaseModel):
    """Схема смены пароля."""
    old_password: str = Field(..., min_length=1, description="Текущий пароль")
    new_password: str = Field(..., min_length=6, max_length=128, description="Новый пароль (мин. 6 символов)")
