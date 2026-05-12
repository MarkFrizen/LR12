"""
CRUD-операции для сущности «Заказ».

Реализует:
- Автоматическую установку buyer_name из current_user (защита от подмены).
- Уменьшение остатка товара на складе при создании заказа.
- Ролевую проверку при обновлении статуса.
"""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import (
    InsufficientStockError,
    OrderNotFoundError,
    ProductNotFoundError,
    SellerNotFoundError,
)
from app.logger import get_logger
from app.models.order import OrderCreate, OrderORM, OrderUpdate
from app.models.product import ProductORM
from app.models.seller import SellerORM

logger = get_logger(__name__)

# Роли, которым разрешено управлять любыми заказами
_MODERATION_ROLES = {"admin", "moderator"}


class OrderService:
    """Сервис для управления заказами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: OrderCreate, buyer_username: str) -> OrderORM:
        """
        Создать новый заказ.

        buyer_name устанавливается из переданного buyer_username
        (берётся из current_user.username на уровне роутера).

        Args:
            data: Данные заказа.
            buyer_username: Имя покупателя (из JWT-токена).

        Returns:
            OrderORM — сохранённый заказ.

        Raises:
            SellerNotFoundError: Если продавец не найден.
            ProductNotFoundError: Если товар не найден.
            InsufficientStockError: Если недостаточно товара на складе.
        """
        seller = await self.db.execute(
            select(SellerORM).where(SellerORM.id == data.seller_id)
        )
        if seller.scalar_one_or_none() is None:
            logger.warning("Попытка создать заказ у несуществующего продавца id=%d", data.seller_id)
            raise SellerNotFoundError(data.seller_id)

        product = await self.db.execute(
            select(ProductORM).where(ProductORM.id == data.product_id)
        )
        product_obj = product.scalar_one_or_none()
        if product_obj is None:
            logger.warning("Попытка создать заказ на несуществующий товар id=%d", data.product_id)
            raise ProductNotFoundError(data.product_id)

        if product_obj.stock < data.quantity:
            logger.warning("Недостаточно товара id=%d: запрошено %d, доступно %d",
                           data.product_id, data.quantity, product_obj.stock)
            raise InsufficientStockError(
                product_id=data.product_id,
                requested=data.quantity,
                available=product_obj.stock,
            )

        product_obj.stock -= data.quantity
        total_price: Decimal = product_obj.price * Decimal(data.quantity)

        # buyer_name берётся из JWT, а не из тела запроса
        order = OrderORM(
            product_id=data.product_id,
            seller_id=data.seller_id,
            buyer_name=buyer_username,
            quantity=data.quantity,
            total_price=total_price,
        )
        self.db.add(order)
        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Создан заказ id=%d товар=%d покупатель='%s' сумма=%s",
                     order.id, order.product_id, order.buyer_name, order.total_price)
        return order

    async def get_by_id(self, order_id: int) -> OrderORM:
        """Получить заказ по ID."""
        result = await self.db.execute(
            select(OrderORM).where(OrderORM.id == order_id)
        )
        order = result.scalar_one_or_none()
        if order is None:
            logger.warning("Заказ id=%d не найден", order_id)
            raise OrderNotFoundError(order_id)
        logger.debug("Получен заказ id=%d статус='%s'", order_id, order.status)
        return order

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        seller_id: int | None = None,
        status: str | None = None,
    ) -> list[OrderORM]:
        """Получить список заказов с фильтрацией."""
        query = select(OrderORM)
        if seller_id is not None:
            query = query.where(OrderORM.seller_id == seller_id)
        if status is not None:
            query = query.where(OrderORM.status == status)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        orders = list(result.scalars().all())
        logger.debug("Запрошен список заказов: %d записей", len(orders))
        return orders

    async def update_status(
        self, order_id: int, data: OrderUpdate, user_id: int, user_role: str
    ) -> OrderORM:
        """
        Обновить статус заказа.

        Args:
            order_id: ID заказа.
            data: Новый статус.
            user_id: ID текущего пользователя.
            user_role: Роль текущего пользователя.

        Returns:
            OrderORM — обновлённый заказ.
        """
        order = await self.get_by_id(order_id)

        # Проверка прав
        if user_role not in _MODERATION_ROLES and order.seller_id != user_id:
            logger.warning("Пользователь id=%d попытался изменить статус заказа id=%d",
                           user_id, order_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для изменения статуса заказа.",
            )

        old_status = order.status
        order.status = data.status
        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Обновлён статус заказа id=%d: '%s' → '%s' (user_id=%d)",
                     order_id, old_status, order.status, user_id)
        return order

    async def delete(self, order_id: int) -> None:
        """Удалить заказ (только для администратора)."""
        order = await self.get_by_id(order_id)
        await self.db.delete(order)
        await self.db.flush()
        logger.info("Удалён заказ id=%d", order_id)
