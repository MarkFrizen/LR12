"""
CRUD-операции для сущности «Отзыв».
"""

from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ReviewNotFoundError, SellerNotFoundError, ProductNotFoundError
from app.logger import get_logger
from app.models.product import ProductORM
from app.models.seller import SellerORM
from app.models.review import ReviewCreate, ReviewORM, ReviewUpdate

logger = get_logger(__name__)


class ReviewService:
    """Сервис для управления отзывами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ReviewCreate) -> ReviewORM:
        seller = await self.db.execute(
            select(SellerORM).where(SellerORM.id == data.seller_id)
        )
        if seller.scalar_one_or_none() is None:
            logger.warning("Попытка создать отзыв у несуществующего продавца id=%d", data.seller_id)
            raise SellerNotFoundError(data.seller_id)

        product = await self.db.execute(
            select(ProductORM).where(ProductORM.id == data.product_id)
        )
        if product.scalar_one_or_none() is None:
            logger.warning("Попытка создать отзыв на несуществующий товар id=%d", data.product_id)
            raise ProductNotFoundError(data.product_id)

        review = ReviewORM(**data.model_dump())
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)

        # Пересчёт рейтинга продавца
        avg_rating = await self.db.execute(
            select(func.avg(ReviewORM.rating)).where(
                ReviewORM.seller_id == data.seller_id
            )
        )
        avg = avg_rating.scalar()
        if avg is not None:
            seller_orm = await self.db.execute(
                select(SellerORM).where(SellerORM.id == data.seller_id)
            )
            seller_obj = seller_orm.scalar_one()
            old_rating = seller_obj.rating
            seller_obj.rating = round(float(avg), 2)
            await self.db.flush()
            logger.info("Обновлён рейтинг продавца id=%d: %.2f → %.2f",
                        data.seller_id, old_rating, seller_obj.rating)

        logger.info("Создан отзыв id=%d товар=%d оценка=%d покупатель='%s'",
                     review.id, review.product_id, review.rating, review.buyer_name)
        return review

    async def get_by_id(self, review_id: int) -> ReviewORM:
        result = await self.db.execute(
            select(ReviewORM).where(ReviewORM.id == review_id)
        )
        review = result.scalar_one_or_none()
        if review is None:
            logger.warning("Отзыв id=%d не найден", review_id)
            raise ReviewNotFoundError(review_id)
        logger.debug("Получен отзыв id=%d", review_id)
        return review

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        product_id: Optional[int] = None,
        seller_id: Optional[int] = None,
    ) -> list[ReviewORM]:
        query = select(ReviewORM)
        if product_id is not None:
            query = query.where(ReviewORM.product_id == product_id)
        if seller_id is not None:
            query = query.where(ReviewORM.seller_id == seller_id)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        reviews = list(result.scalars().all())
        logger.debug("Запрошен список отзывов: %d записей", len(reviews))
        return reviews

    async def update(
        self, review_id: int, data: ReviewUpdate
    ) -> ReviewORM:
        review = await self.get_by_id(review_id)
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(review, field, value)
        await self.db.flush()
        await self.db.refresh(review)
        logger.info("Обновлён отзыв id=%d поля=%s", review_id, list(update_data.keys()))
        return review

    async def delete(self, review_id: int) -> None:
        review = await self.get_by_id(review_id)
        await self.db.delete(review)
        await self.db.flush()
        logger.info("Удалён отзыв id=%d", review_id)
