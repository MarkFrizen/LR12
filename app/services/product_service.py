"""
CRUD-операции для сущности «Товар».
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ProductNotFoundError, SellerNotFoundError
from app.logger import get_logger
from app.models.product import ProductCreate, ProductORM, ProductUpdate
from app.models.seller import SellerORM

logger = get_logger(__name__)


class ProductService:
    """Сервис для управления товарами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ProductCreate) -> ProductORM:
        seller = await self.db.execute(
            select(SellerORM).where(SellerORM.id == data.seller_id)
        )
        if seller.scalar_one_or_none() is None:
            logger.warning("Попытка создать товар у несуществующего продавца id=%d", data.seller_id)
            raise SellerNotFoundError(data.seller_id)

        product = ProductORM(**data.model_dump())
        self.db.add(product)
        await self.db.flush()
        await self.db.refresh(product)
        logger.info("Создан товар id=%d name='%s' price=%s seller_id=%d",
                     product.id, product.name, product.price, product.seller_id)
        return product

    async def get_by_id(self, product_id: int) -> ProductORM:
        result = await self.db.execute(
            select(ProductORM).where(ProductORM.id == product_id)
        )
        product = result.scalar_one_or_none()
        if product is None:
            logger.warning("Товар id=%d не найден", product_id)
            raise ProductNotFoundError(product_id)
        logger.debug("Получен товар id=%d", product_id)
        return product

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        seller_id: Optional[int] = None,
        category: Optional[str] = None,
    ) -> list[ProductORM]:
        query = select(ProductORM)
        if seller_id is not None:
            query = query.where(ProductORM.seller_id == seller_id)
        if category is not None:
            query = query.where(ProductORM.category == category)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        products = list(result.scalars().all())
        logger.debug("Запрошен список товаров: %d записей (seller_id=%s, category=%s)",
                     len(products), seller_id, category)
        return products

    async def update(
        self, product_id: int, data: ProductUpdate
    ) -> ProductORM:
        product = await self.get_by_id(product_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await self.db.flush()
        await self.db.refresh(product)
        logger.info("Обновлён товар id=%d поля=%s", product_id, list(update_data.keys()))
        return product

    async def delete(self, product_id: int) -> None:
        product = await self.get_by_id(product_id)
        await self.db.delete(product)
        await self.db.flush()
        logger.info("Удалён товар id=%d name='%s'", product_id, product.name)
