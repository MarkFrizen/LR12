"""
CRUD-операции для сущности «Заказ».
"""

from decimal import Decimal

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


class OrderService:
    """Сервис для управления заказами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: OrderCreate) -> OrderORM:
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

        order = OrderORM(
            product_id=data.product_id,
            seller_id=data.seller_id,
            buyer_name=data.buyer_name,
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
        self, order_id: int, data: OrderUpdate
    ) -> OrderORM:
        order = await self.get_by_id(order_id)
        old_status = order.status
        order.status = data.status
        await self.db.flush()
        await self.db.refresh(order)
        logger.info("Обновлён статус заказа id=%d: '%s' → '%s'", order_id, old_status, order.status)
        return order

    async def delete(self, order_id: int) -> None:
        order = await self.get_by_id(order_id)
        await self.db.delete(order)
        await self.db.flush()
        logger.info("Удалён заказ id=%d", order_id)
