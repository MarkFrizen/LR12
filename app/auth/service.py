"""
Сервис аутентификации: регистрация, вход, управление пользователями.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import (
    MODERATION_ROLES,
    UserCreate,
    UserLogin,
    UserORM,
    UserRole,
    UserUpdate,
)
from app.auth.utils import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.exceptions import MarketPlaceError
from app.logger import get_logger

logger = get_logger(__name__)


class AuthService:
    """
    Сервис аутентификации и управления пользователями.
    Инкапсулирует всю бизнес-логику работы с пользователями.
    (Single Responsibility Principle)
    """

    async def register(self, db: AsyncSession, data: UserCreate) -> UserORM:
        """
        Зарегистрировать нового пользователя.

        Args:
            db: Сессия БД.
            data: Данные нового пользователя.

        Returns:
            UserORM — сохранённый пользователь.

        Raises:
            MarketPlaceError: Если username или email уже заняты.
        """
        # Проверка уникальности username
        existing = await db.execute(
            select(UserORM).where(UserORM.username == data.username)
        )
        if existing.scalar_one_or_none():
            raise MarketPlaceError(
                f"Имя пользователя '{data.username}' уже занято.", 409
            )

        # Проверка уникальности email
        existing = await db.execute(
            select(UserORM).where(UserORM.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise MarketPlaceError(
                f"Email '{data.email}' уже зарегистрирован.", 409
            )

        user = UserORM(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
            role=data.role.value if isinstance(data.role, UserRole) else data.role,
            full_name=data.full_name,
            phone=data.phone,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("Зарегистрирован пользователь id=%d username='%s' роль='%s'",
                     user.id, user.username, user.role)
        return user

    async def authenticate(
        self, db: AsyncSession, data: UserLogin
    ) -> tuple[UserORM, str]:
        """
        Аутентифицировать пользователя и вернуть JWT-токен.

        Args:
            db: Сессия БД.
            data: Учётные данные.

        Returns:
            Кортеж (UserORM, access_token).

        Raises:
            MarketPlaceError: Если пользователь не найден,
                              пароль неверен или пользователь заблокирован.
        """
        result = await db.execute(
            select(UserORM).where(UserORM.username == data.username)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise MarketPlaceError("Неверное имя пользователя или пароль.", 401)

        if not verify_password(data.password, user.hashed_password):
            logger.warning("Неудачная попытка входа для '%s' (неверный пароль)", data.username)
            raise MarketPlaceError("Неверное имя пользователя или пароль.", 401)

        if not user.is_active:
            logger.warning("Попытка входа заблокированным пользователем '%s'", data.username)
            raise MarketPlaceError("Пользователь заблокирован.", 403)

        token = create_access_token({"sub": str(user.id), "role": user.role})
        logger.info("Успешный вход пользователя id=%d username='%s'", user.id, user.username)
        return user, token

    async def get_by_id(self, db: AsyncSession, user_id: int) -> UserORM | None:
        """Получить пользователя по ID."""
        result = await db.execute(
            select(UserORM).where(UserORM.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_username(
        self, db: AsyncSession, username: str
    ) -> UserORM | None:
        """Получить пользователя по имени."""
        result = await db.execute(
            select(UserORM).where(UserORM.username == username)
        )
        return result.scalar_one_or_none()

    async def update_profile(
        self, db: AsyncSession, user_id: int, data: UserUpdate
    ) -> UserORM:
        """Обновить профиль пользователя."""
        user = await self.get_by_id(db, user_id)
        if not user:
            raise MarketPlaceError("Пользователь не найден.", 404)

        update_data = data.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"] != user.email:
            existing = await db.execute(
                select(UserORM).where(UserORM.email == update_data["email"])
            )
            if existing.scalar_one_or_none():
                raise MarketPlaceError(
                    f"Email '{update_data['email']}' уже занят.", 409
                )

        for field, value in update_data.items():
            setattr(user, field, value)

        await db.flush()
        await db.refresh(user)
        return user

    async def list_users(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ) -> list[UserORM]:
        """Список всех пользователей (для админа)."""
        result = await db.execute(
            select(UserORM).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def change_role(
        self, db: AsyncSession, user_id: int, new_role: UserRole
    ) -> UserORM:
        """Сменить роль пользователя (для админа)."""
        user = await self.get_by_id(db, user_id)
        if not user:
            raise MarketPlaceError("Пользователь не найден.", 404)
        old_role = user.role
        user.role = new_role.value if isinstance(new_role, UserRole) else new_role
        await db.flush()
        await db.refresh(user)
        logger.info("Смена роли пользователя id=%d: '%s' → '%s'", user_id, old_role, user.role)
        return user

    async def toggle_active(
        self, db: AsyncSession, user_id: int
    ) -> UserORM:
        """Заблокировать / разблокировать пользователя (для админа)."""
        user = await self.get_by_id(db, user_id)
        if not user:
            raise MarketPlaceError("Пользователь не найден.", 404)
        user.is_active = not user.is_active
        await db.flush()
        await db.refresh(user)
        action = "разблокирован" if user.is_active else "заблокирован"
        logger.info("Пользователь id=%d username='%s' %s", user_id, user.username, action)
        return user


# Единственный экземпляр сервиса (можно мокать в тестах через Depends)
auth_service = AuthService()
