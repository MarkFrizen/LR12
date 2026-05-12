"""
CRUD-операции для сущности «Отзыв».

Реализует:
- Автоматическую установку buyer_name из current_user (защита от подмены).
- Пересчёт рейтинга продавца после создания отзыва.
- Исправлен N+1 запрос: объект продавца сохраняется после первого SELECT.
"""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ReviewNotFoundError, SellerNotFoundError, ProductNotFoundError
from app.logger import get_logger
from app.models.product import ProductORM
from app.models.seller import SellerORM
from app.models.review import ReviewCreate, ReviewORM, ReviewUpdate

logger = get_logger(__name__)

# Роли, которым разрешено управлять любыми отзывами
_MODERATION_ROLES = {"admin", "moderator"}


class ReviewService:
    """Сервис для управления отзывами."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ReviewCreate, buyer_username: str) -> ReviewORM:
        """
        Создать новый отзыв.

        buyer_name устанавливается из переданного buyer_username
        (берётся из current_user.username на уровне роутера).
        Объект продавца запрашивается один раз и переиспользуется
        для обновления рейтинга (без дублирующего SELECT).

        Args:
            data: Данные отзыва.
            buyer_username: Имя покупателя (из JWT-токена).

        Returns:
            ReviewORM — сохранённый отзыв.

        Raises:
            SellerNotFoundError: Если продавец не найден.
            ProductNotFoundError: Если товар не найден.
        """
        # Запрос 1: получить продавца (сохраняем объект для переиспользования)
        seller_result = await self.db.execute(
            select(SellerORM).where(SellerORM.id == data.seller_id)
        )
        seller_obj = seller_result.scalar_one_or_none()
        if seller_obj is None:
            logger.warning("Попытка создать отзыв у несуществующего продавца id=%d", data.seller_id)
            raise SellerNotFoundError(data.seller_id)

        # Запрос 2: проверить существование товара
        product = await self.db.execute(
            select(ProductORM).where(ProductORM.id == data.product_id)
        )
        if product.scalar_one_or_none() is None:
            logger.warning("Попытка создать отзыв на несуществующий товар id=%d", data.product_id)
            raise ProductNotFoundError(data.product_id)

        # buyer_name берётся из JWT, не из тела запроса
        review_data = data.model_dump(exclude={"buyer_name"})
        review = ReviewORM(**review_data, buyer_name=buyer_username)
        self.db.add(review)
        await self.db.flush()
        await self.db.refresh(review)

        # Пересчёт рейтинга продавца (используем сохранённый seller_obj, без нового запроса)
        avg_rating = await self.db.execute(
            select(func.avg(ReviewORM.rating)).where(
                ReviewORM.seller_id == data.seller_id
            )
        )
        avg = avg_rating.scalar()
        if avg is not None:
            old_rating = seller_obj.rating
            seller_obj.rating = round(float(avg), 2)
            await self.db.flush()
            logger.info("Обновлён рейтинг продавца id=%d: %.2f → %.2f",
                        data.seller_id, old_rating, seller_obj.rating)

        logger.info("Создан отзыв id=%d товар=%d оценка=%d покупатель='%s'",
                     review.id, review.product_id, review.rating, review.buyer_name)
        return review

    async def get_by_id(self, review_id: int) -> ReviewORM:
        """Получить отзыв по ID."""
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
        """Получить список отзывов."""
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
        self, review_id: int, data: ReviewUpdate, user_id: int, user_role: str
    ) -> ReviewORM:
        """
        Обновить отзыв.

        Args:
            review_id: ID отзыва.
            data: Новые данные (rating, comment).
            user_id: ID текущего пользователя.
            user_role: Роль текущего пользователя.

        Returns:
            ReviewORM — обновлённый отзыв.

        Raises:
            HTTPException(403): Если пользователь не является автором
                                и не имеет модераторской роли.
        """
        review = await self.get_by_id(review_id)

        # Проверка прав: автор или модератор/админ
        if user_role not in _MODERATION_ROLES:
            logger.warning("Пользователь id=%d попытался изменить отзыв id=%d (автор='%s')",
                           user_id, review_id, review.buyer_name)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для изменения этого отзыва.",
            )

        # Явное обновление полей (вместо setattr — массовое присвоение)
        if data.rating is not None:
            review.rating = data.rating
        if data.comment is not None:
            review.comment = data.comment

        await self.db.flush()
        await self.db.refresh(review)
        logger.info("Обновлён отзыв id=%d (user_id=%d)", review_id, user_id)
        return review

    async def delete(
        self, review_id: int, user_id: int, user_role: str
    ) -> None:
        """
        Удалить отзыв.

        Args:
            review_id: ID отзыва.
            user_id: ID текущего пользователя.
            user_role: Роль текущего пользователя.

        Raises:
            HTTPException(403): Если пользователь не является автором
                                и не имеет модераторской роли.
        """
        review = await self.get_by_id(review_id)

        # Проверка прав: автор или модератор/админ
        if user_role not in _MODERATION_ROLES and review.buyer_name != str(user_id):
            logger.warning("Пользователь id=%d попытался удалить отзыв id=%d (автор='%s')",
                           user_id, review_id, review.buyer_name)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для удаления этого отзыва.",
            )

        await self.db.delete(review)
        await self.db.flush()
        logger.info("Удалён отзыв id=%d (user_id=%d)", review_id, user_id)
