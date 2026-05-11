"""
REST-эндпоинты для аутентификации и управления пользователями.

Доступные операции:
- POST /api/v1/auth/register        — регистрация
- POST /api/v1/auth/login           — вход, получение JWT
- GET  /api/v1/auth/me              — профиль текущего пользователя
- PATCH /api/v1/auth/me             — обновление профиля
- GET  /api/v1/auth/users           — список пользователей (admin)
- PATCH /api/v1/auth/users/{id}/role  — смена роли (admin)
- POST /api/v1/auth/users/{id}/toggle — блокировка (admin)
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_user,
    require_admin,
)
from app.auth.models import (
    TokenResponse,
    UserCreate,
    UserLogin,
    UserORM,
    UserResponse,
    UserRole,
    UserUpdate,
)
from app.auth.service import auth_service
from app.database import get_db

router = APIRouter(prefix="/api/v1/auth", tags=["Аутентификация"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Зарегистрировать нового пользователя."""
    return await auth_service.register(db, data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Войти в систему, получить JWT-токен."""
    _, token = await auth_service.authenticate(db, data)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_profile(
    current_user: UserORM = Depends(get_current_user),
):
    """Получить профиль текущего пользователя."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserORM = Depends(get_current_user),
):
    """Обновить свой профиль."""
    return await auth_service.update_profile(db, current_user.id, data)


# ─── Админ-эндпоинты ───

@router.get(
    "/users",
    response_model=list[UserResponse],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _admin: UserORM = Depends(require_admin),
):
    """[Admin] Список всех пользователей."""
    return await auth_service.list_users(db, skip=skip, limit=limit)


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
)
async def change_user_role(
    user_id: int,
    new_role: UserRole,
    db: AsyncSession = Depends(get_db),
    _admin: UserORM = Depends(require_admin),
):
    """[Admin] Сменить роль пользователя."""
    return await auth_service.change_role(db, user_id, new_role)


@router.post(
    "/users/{user_id}/toggle",
    response_model=UserResponse,
)
async def toggle_user_active(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: UserORM = Depends(require_admin),
):
    """[Admin] Заблокировать / разблокировать пользователя."""
    return await auth_service.toggle_active(db, user_id)
