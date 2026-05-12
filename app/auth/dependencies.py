"""
Зависимости FastAPI для аутентификации и авторизации.

Содержит:
- get_current_user — извлекает текущего пользователя из JWT
- RoleChecker — фабрика для проверки ролей
- get_current_admin_user — для админ-эндпоинтов
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.config import auth_settings
from app.auth.models import UserORM, UserRole
from app.auth.service import auth_service
from app.database import get_db

# Bearer-схема для извлечения токена из заголовка Authorization
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    token: str | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserORM:
    """
    Извлечь текущего пользователя из JWT-токена.

    Args:
        token: JWT-токен из заголовка Authorization.
        db: Сессия БД.

    Returns:
        UserORM — текущий пользователь.

    Raises:
        HTTPException(401): Если токен отсутствует, недействителен
                            или пользователь не найден.
    """
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Требуется аутентификация.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительный токен.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token.credentials,
            auth_settings.jwt_secret_key,
            algorithms=[auth_settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await auth_service.get_by_id(db, int(user_id))
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def role_required(*allowed_roles: UserRole):
    """
    Фабрика зависимости, проверяющей, что пользователь имеет одну из ролей.

    Args:
        allowed_roles: Разрешённые роли.

    Returns:
        Зависимость FastAPI.
    """
    async def _role_checker(
        current_user: UserORM = Depends(get_current_user),
    ) -> UserORM:
        if current_user.role not in {r.value for r in allowed_roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции.",
            )
        return current_user
    return _role_checker


# Предопределённые проверки ролей
require_admin = role_required(UserRole.ADMIN)
require_moderator = role_required(UserRole.ADMIN, UserRole.MODERATOR)
require_seller = role_required(UserRole.ADMIN, UserRole.MODERATOR, UserRole.SELLER)
require_buyer = role_required(UserRole.ADMIN, UserRole.BUYER)
