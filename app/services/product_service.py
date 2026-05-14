"""
CRUD-операции для сущности «Товар».

Реализует проверку прав доступа: продавец может изменять только свои товары,
администратор и модератор — любые.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select

from app.auth.models import MODERATION_ROLE_VALUES
from app.exceptions import ProductNotFoundError, SellerNotFoundError
from app.logger import get_logger
from app.models.product import ProductCreate, ProductORM, ProductUpdate
from app.models.seller import SellerORM
from app.services.base import BaseService

logger = get_logger(__name__)


class ProductService(BaseService):
    """Сервис для управления товарами."""

    async def create(self, data: ProductCreate, user_id: int) -> ProductORM:
        """
        Создать новый товар.

        Args:
            data: Данные товара.
            user_id: ID текущего пользователя (для логирования).

        Returns:
            ProductORM — сохранённый товар.

        Raises:
            SellerNotFoundError: Если продавец не найден.
        """
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
        logger.info("Создан товар id=%d name='%s' price=%s seller_id=%d (user_id=%d)",
                     product.id, product.name, product.price, product.seller_id, user_id)
        return product

    async def get_by_id(self, product_id: int) -> ProductORM:
        """Получить товар по ID."""
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
        """Получить список товаров с фильтрацией."""
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
        self, product_id: int, data: ProductUpdate, user_id: int, user_role: str
    ) -> ProductORM:
        """
        Обновить товар.

        Args:
            product_id: ID товара.
            data: Новые данные.
            user_id: ID текущего пользователя.
            user_role: Роль текущего пользователя.

        Returns:
            ProductORM — обновлённый товар.

        Raises:
            HTTPException(403): Если пользователь не является владельцем
                                и не имеет модераторской роли.
        """
        product = await self.get_by_id(product_id)

        # Проверка прав: владелец товара или модератор/админ
        if user_role not in MODERATION_ROLE_VALUES and product.seller_id != user_id:
            logger.warning("Пользователь id=%d попытался изменить товар id=%d продавца id=%d",
                           user_id, product_id, product.seller_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для изменения этого товара.",
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        await self.db.flush()
        await self.db.refresh(product)
        logger.info("Обновлён товар id=%d поля=%s (user_id=%d)",
                     product_id, list(update_data.keys()), user_id)
        return product

    async def delete(self, product_id: int) -> None:
        """Удалить товар (только для администратора)."""
        product = await self.get_by_id(product_id)
        await self.db.delete(product)
        await self.db.flush()
        logger.info("Удалён товар id=%d name='%s'", product_id, product.name)
