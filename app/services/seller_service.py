"""
CRUD-операции для сущности «Продавец».
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import DuplicateEmailError, SellerNotFoundError
from app.logger import get_logger
from app.models.seller import SellerCreate, SellerORM, SellerUpdate

logger = get_logger(__name__)


class SellerService:
    """Сервис для управления продавцами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: SellerCreate) -> SellerORM:
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
        logger.info("Создан продавец id=%d name='%s' email='%s'", seller.id, seller.name, seller.email)
        return seller

    async def get_by_id(self, seller_id: int) -> SellerORM:
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
        result = await self.db.execute(
            select(SellerORM).offset(skip).limit(limit)
        )
        sellers = list(result.scalars().all())
        logger.debug("Запрошен список продавцов: %d записей", len(sellers))
        return sellers

    async def update(
        self, seller_id: int, data: SellerUpdate
    ) -> SellerORM:
        seller = await self.get_by_id(seller_id)
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
        logger.info("Обновлён продавец id=%d поля=%s", seller_id, list(update_data.keys()))
        return seller

    async def delete(self, seller_id: int) -> None:
        seller = await self.get_by_id(seller_id)
        await self.db.delete(seller)
        await self.db.flush()
        logger.info("Удалён продавец id=%d name='%s'", seller_id, seller.name)
