"""
Тесты сервиса отзывов.

Покрытие: создание отзыва, обновление рейтинга продавца,
чтение, обновление, удаление, обработка NotFound.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.exceptions import ReviewNotFoundError
from app.models.product import ProductCreate
from app.models.review import ReviewCreate, ReviewUpdate
from app.models.seller import SellerCreate
from app.services.product_service import ProductService
from app.services.review_service import ReviewService
from app.services.seller_service import SellerService


_TEST_USER_ID = 1
_TEST_MOD_ROLE = "admin"
_TEST_BUYER = "test_critic"


@pytest.mark.asyncio
async def test_create_review(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="RevSeller", email="rev@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="ReviewedItem", price=100, stock=5
    ), user_id=_TEST_USER_ID)
    service = ReviewService(db=db_session)
    review = await service.create(
        ReviewCreate(product_id=product.id, seller_id=seller.id, rating=5, comment="Great!"),
        buyer_username=_TEST_BUYER,
    )
    assert review.id is not None
    assert review.rating == 5
    assert review.buyer_name == _TEST_BUYER


@pytest.mark.asyncio
async def test_review_updates_seller_rating(db_session: AsyncSession):
    seller_svc = SellerService(db=db_session)
    seller = await seller_svc.create(
        SellerCreate(name="RatingTest", email="rt@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="RatingItem", price=50, stock=10
    ), user_id=_TEST_USER_ID)
    service = ReviewService(db=db_session)

    # Первый отзыв: 5
    await service.create(
        ReviewCreate(product_id=product.id, seller_id=seller.id, rating=5),
        buyer_username="A",
    )
    seller1 = await seller_svc.get_by_id(seller.id)
    assert seller1.rating == 5.0

    # Второй отзыв: 3 → среднее (5+3)/2 = 4.0
    await service.create(
        ReviewCreate(product_id=product.id, seller_id=seller.id, rating=3),
        buyer_username="B",
    )
    seller2 = await seller_svc.get_by_id(seller.id)
    assert seller2.rating == 4.0


@pytest.mark.asyncio
async def test_get_review_by_id(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="GetRev", email="gr@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="GetRevItem", price=10, stock=5
    ), user_id=_TEST_USER_ID)
    service = ReviewService(db=db_session)
    review = await service.create(
        ReviewCreate(product_id=product.id, seller_id=seller.id, rating=4),
        buyer_username="Me",
    )
    found = await service.get_by_id(review.id)
    assert found.buyer_name == "Me"


@pytest.mark.asyncio
async def test_update_review(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="UpdRev", email="ur@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="UpdItem", price=10, stock=5
    ), user_id=_TEST_USER_ID)
    service = ReviewService(db=db_session)
    # Сначала создаем отзыв
    review = await service.create(
        ReviewCreate(product_id=product.id, seller_id=seller.id, rating=2, comment="Bad"),
        buyer_username="U",
    )
    
    # Затем пытаемся его обновить без прав
    with patch("app.services.review_service.logger") as mock_logger:
        with pytest.raises(Exception) as exc_info:
            await service.update(
                review.id, ReviewUpdate(rating=4, comment="Updated"),
                user_id=_TEST_USER_ID, user_role="buyer",  # не модератор и не автор
            )
        # Проверяем, что это HTTPException с кодом 403
        from fastapi import HTTPException
        assert isinstance(exc_info.value, HTTPException)
        assert exc_info.value.status_code == 403
        mock_logger.warning.assert_called_once_with(
            "Пользователь id=%d попытался изменить отзыв id=%d (автор='%s')", 
            _TEST_USER_ID, review.id, "U"
        )
    # Обновляем отзыв с правами модератора
    updated = await service.update(
        review.id, ReviewUpdate(rating=4, comment="Updated"),
        user_id=_TEST_USER_ID, user_role=_TEST_MOD_ROLE,
    )
    assert updated.rating == 4
    assert updated.comment == "Updated"
    assert updated.rating == 4
    assert updated.comment == "Updated"


@pytest.mark.asyncio
async def test_delete_review(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="DelRev", email="dr@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="DelItem", price=5, stock=5
    ), user_id=_TEST_USER_ID)
    service = ReviewService(db=db_session)
    review = await service.create(
        ReviewCreate(product_id=product.id, seller_id=seller.id, rating=3),
        buyer_username="X",
    )
    await service.delete(review.id, user_id=_TEST_USER_ID, user_role=_TEST_MOD_ROLE)
    # Сначала создаем отзыв
    review = await service.create(
        ReviewCreate(product_id=product.id, seller_id=seller.id, rating=3),
        buyer_username="X",
    )
    
    # Затем удаляем его
    with patch("app.services.review_service.logger") as mock_logger:
        await service.delete(review.id, user_id=_TEST_USER_ID, user_role=_TEST_MOD_ROLE)
        mock_logger.info.assert_called_once_with(
            "Удалён отзыв id=%d (user_id=%d)", review.id, _TEST_USER_ID
        )
    with pytest.raises(ReviewNotFoundError):
        await service.get_by_id(review.id)
