"""
CRUD-операции для сущности «Комиссия».

Все операции с комиссиями доступны только администраторам
(защита настроена на уровне роутера).
"""

from typing import Optional

from sqlalchemy import select

from app.exceptions import (
    CommissionNotFoundError,
    SellerNotFoundError,
    OrderNotFoundError,
)
from app.logger import get_logger
from app.models.commission import CommissionCreate, CommissionORM, CommissionUpdate
from app.models.seller import SellerORM
from app.models.order import OrderORM
from app.services.base import BaseService

logger = get_logger(__name__)


class CommissionService(BaseService):
    """Сервис для управления комиссиями."""

    async def create(self, data: CommissionCreate) -> CommissionORM:
        """
        Создать новую комиссию.

        Args:
            data: Данные комиссии.

        Returns:
            CommissionORM — сохранённая комиссия.

        Raises:
            SellerNotFoundError: Если продавец не найден.
            OrderNotFoundError: Если заказ не найден.
        """
        seller = await self.db.execute(
            select(SellerORM).where(SellerORM.id == data.seller_id)
        )
        if seller.scalar_one_or_none() is None:
            logger.warning("Попытка создать комиссию у несуществующего продавца id=%d", data.seller_id)
            raise SellerNotFoundError(data.seller_id)

        order = await self.db.execute(
            select(OrderORM).where(OrderORM.id == data.order_id)
        )
        if order.scalar_one_or_none() is None:
            logger.warning("Попытка создать комиссию для несуществующего заказа id=%d", data.order_id)
            raise OrderNotFoundError(data.order_id)

        commission = CommissionORM(**data.model_dump())
        self.db.add(commission)
        await self.db.flush()
        await self.db.refresh(commission)
        logger.info("Создана комиссия id=%d заказ=%d продавец=%d сумма=%s",
                     commission.id, commission.order_id, commission.seller_id, commission.amount)
        return commission

    async def get_by_id(self, commission_id: int) -> CommissionORM:
        """Получить комиссию по ID."""
        result = await self.db.execute(
            select(CommissionORM).where(CommissionORM.id == commission_id)
        )
        commission = result.scalar_one_or_none()
        if commission is None:
            logger.warning("Комиссия id=%d не найдена", commission_id)
            raise CommissionNotFoundError(commission_id)
        logger.debug("Получена комиссия id=%d", commission_id)
        return commission

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        seller_id: Optional[int] = None,
        status: Optional[str] = None,
    ) -> list[CommissionORM]:
        """Получить список комиссий."""
        query = select(CommissionORM)
        if seller_id is not None:
            query = query.where(CommissionORM.seller_id == seller_id)
        if status is not None:
            query = query.where(CommissionORM.status == status)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        commissions = list(result.scalars().all())
        logger.debug("Запрошен список комиссий: %d записей", len(commissions))
        return commissions

    async def update(
        self, commission_id: int, data: CommissionUpdate
    ) -> CommissionORM:
        """Обновить комиссию (только для администратора)."""
        commission = await self.get_by_id(commission_id)
        update_data = data.model_dump(exclude_unset=True)
        old_status = commission.status
        for field, value in update_data.items():
            setattr(commission, field, value)
        await self.db.flush()
        await self.db.refresh(commission)
        logger.info("Обновлена комиссия id=%d статус: '%s' → '%s'",
                     commission_id, old_status, commission.status)
        return commission

    async def delete(self, commission_id: int) -> None:
        """Удалить комиссию (только для администратора)."""
        commission = await self.get_by_id(commission_id)
        await self.db.delete(commission)
        await self.db.flush()
        logger.info("Удалена комиссия id=%d", commission_id)
