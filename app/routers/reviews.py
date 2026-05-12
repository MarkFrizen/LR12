"""
REST-эндпоинты для отзывов.

Защита по ролям:
    - POST   / — только buyer, admin  (require_buyer)
    - GET    / — любой аутентифицированный
    - GET    /{id} — любой аутентифицированный
    - PATCH  /{id} — автор отзыва, admin, moderator
    - DELETE /{id} — автор отзыва, admin, moderator
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_buyer, require_moderator
from app.auth.models import UserORM
from app.database import get_db
from app.models.review import ReviewCreate, ReviewResponse, ReviewUpdate
from app.services.review_service import ReviewService

router = APIRouter(prefix="/api/v1/reviews", tags=["Отзывы"])


async def get_review_service(db: AsyncSession = Depends(get_db)) -> ReviewService:
    """Фабрика сервиса отзывов."""
    return ReviewService(db=db)


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    data: ReviewCreate,
    service: ReviewService = Depends(get_review_service),
    current_user: UserORM = Depends(require_buyer),
):
    """
    Создать новый отзыв.

    Доступно: покупателям и администраторам.
    buyer_name устанавливается автоматически из учётной записи.
    """
    return await service.create(data, buyer_username=current_user.username)


@router.get("/", response_model=list[ReviewResponse])
async def list_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    product_id: Optional[int] = Query(None),
    seller_id: Optional[int] = Query(None),
    service: ReviewService = Depends(get_review_service),
):
    """Получить список отзывов (публичный доступ)."""
    return await service.get_all(
        skip=skip, limit=limit, product_id=product_id, seller_id=seller_id
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(
    review_id: int,
    service: ReviewService = Depends(get_review_service),
):
    """Получить отзыв по ID (публичный доступ)."""
    return await service.get_by_id(review_id)


@router.patch("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    data: ReviewUpdate,
    service: ReviewService = Depends(get_review_service),
    current_user: UserORM = Depends(get_current_user),
):
    """
    Обновить отзыв.

    Доступно: автору отзыва, модератору, администратору.
    """
    return await service.update(review_id, data, user_id=current_user.id, user_role=current_user.role)


@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    service: ReviewService = Depends(get_review_service),
    current_user: UserORM = Depends(get_current_user),
):
    """Удалить отзыв (автор, модератор, администратор)."""
    await service.delete(review_id, user_id=current_user.id, user_role=current_user.role)
