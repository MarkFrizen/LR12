"""
CRUD-операции для сущности «Продавец».

Реализует проверку прав доступа: владелец может изменять только свой профиль,
администратор и модератор — любые.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateEmailError, SellerNotFoundError
from app.logger import get_logger
from app.models.seller import SellerCreate, SellerORM, SellerUpdate

logger = get_logger(__name__)

# Роли, которым разрешено управлять любыми продавцами
_MODERATION_ROLES = {"admin", "moderator"}


class SellerService:
    """Сервис для управления продавцами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: SellerCreate, user_id: int) -> SellerORM:
        """
        Создать нового продавца.

        Args:
            data: Данные продавца.
            user_id: ID текущего пользователя (для логирования).

        Returns:
            SellerORM — сохранённый продавец.

        Raises:
            DuplicateEmailError: Если email уже занят.
        """
        existing = await self.db.execute(
            select(SellerORM).where(SellerORM.email == data.email)
        )
        if existing.scalar_one_or_none() is not None:
            logger.warning("Попытка создать дубликат email: %s", data.email)
            raise DuplicateEmailError(data.email)

        seller = SellerORM(**data.model_dump())
        self.db.add(seller)
        await self.db.flush()
        await self.db.refresh(seller)
        logger.info("Создан продавец id=%d name='%s' email='%s' (user_id=%d)",
                     seller.id, seller.name, seller.email, user_id)
        return seller

    async def get_by_id(self, seller_id: int) -> SellerORM:
        """Получить продавца по ID."""
        result = await self.db.execute(
            select(SellerORM).where(SellerORM.id == seller_id)
        )
        seller = result.scalar_one_or_none()
        if seller is None:
            logger.warning("Продавец id=%d не найден", seller_id)
            raise SellerNotFoundError(seller_id)
        logger.debug("Получен продавец id=%d", seller_id)
        return seller

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> list[SellerORM]:
        """Получить список всех продавцов."""
        result = await self.db.execute(
            select(SellerORM).offset(skip).limit(limit)
        )
        sellers = list(result.scalars().all())
        logger.debug("Запрошен список продавцов: %d записей", len(sellers))
        return sellers

    async def update(
        self, seller_id: int, data: SellerUpdate, user_id: int, user_role: str
    ) -> SellerORM:
        """
        Обновить данные продавца.

        Args:
            seller_id: ID продавца.
            data: Новые данные.
            user_id: ID текущего пользователя.
            user_role: Роль текущего пользователя.

        Returns:
            SellerORM — обновлённый продавец.

        Raises:
            HTTPException(403): Если пользователь не является владельцем
                                и не имеет модераторской роли.
        """
        seller = await self.get_by_id(seller_id)

        # Проверка прав: владелец (по user_id == seller_id) или модератор/админ
        if user_role not in _MODERATION_ROLES and seller.id != user_id:
            logger.warning("Пользователь id=%d попытался изменить продавца id=%d",
                           user_id, seller_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для изменения этого продавца.",
            )

        update_data = data.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] != seller.email:
            existing = await self.db.execute(
                select(SellerORM).where(SellerORM.email == update_data["email"])
            )
            if existing.scalar_one_or_none() is not None:
                logger.warning("Попытка сменить email на занятый: %s", update_data["email"])
                raise DuplicateEmailError(update_data["email"])

        for field, value in update_data.items():
            setattr(seller, field, value)

        await self.db.flush()
        await self.db.refresh(seller)
        logger.info("Обновлён продавец id=%d поля=%s (user_id=%d)",
                     seller_id, list(update_data.keys()), user_id)
        return seller

    async def delete(self, seller_id: int) -> None:
        """Удалить продавца (только для администратора)."""
        seller = await self.get_by_id(seller_id)
        await self.db.delete(seller)
        await self.db.flush()
        logger.info("Удалён продавец id=%d name='%s'", seller_id, seller.name)
