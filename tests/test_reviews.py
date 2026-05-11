"""
Тесты сервиса отзывов.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ReviewNotFoundError
from app.models.product import ProductCreate
from app.models.review import ReviewCreate, ReviewUpdate
from app.models.seller import SellerCreate
from app.services.product_service import ProductService
from app.services.review_service import ReviewService
from app.services.seller_service import SellerService


@pytest.mark.asyncio
async def test_create_review(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="RevSeller", email="rev@test.com")
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="ReviewedItem", price=100, stock=5
    ))
    service = ReviewService(db=db_session)
    review = await service.create(ReviewCreate(
        product_id=product.id,
        seller_id=seller.id,
        buyer_name="Critic",
        rating=5,
        comment="Great!",
    ))
    assert review.id is not None
    assert review.rating == 5


@pytest.mark.asyncio
async def test_review_updates_seller_rating(db_session: AsyncSession):
    seller_svc = SellerService(db=db_session)
    seller = await seller_svc.create(SellerCreate(name="RatingTest", email="rt@test.com"))
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="RatingItem", price=50, stock=10
    ))
    service = ReviewService(db=db_session)

    # Первый отзыв: 5
    await service.create(ReviewCreate(
        product_id=product.id, seller_id=seller.id, buyer_name="A", rating=5
    ))
    seller1 = await seller_svc.get_by_id(seller.id)
    assert seller1.rating == 5.0

    # Второй отзыв: 3 → среднее (5+3)/2 = 4.0
    await service.create(ReviewCreate(
        product_id=product.id, seller_id=seller.id, buyer_name="B", rating=3
    ))
    seller2 = await seller_svc.get_by_id(seller.id)
    assert seller2.rating == 4.0


@pytest.mark.asyncio
async def test_get_review_by_id(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="GetRev", email="gr@test.com")
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="GetRevItem", price=10, stock=5
    ))
    service = ReviewService(db=db_session)
    review = await service.create(ReviewCreate(
        product_id=product.id, seller_id=seller.id, buyer_name="Me", rating=4
    ))
    found = await service.get_by_id(review.id)
    assert found.buyer_name == "Me"


@pytest.mark.asyncio
async def test_update_review(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="UpdRev", email="ur@test.com")
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="UpdItem", price=10, stock=5
    ))
    service = ReviewService(db=db_session)
    review = await service.create(ReviewCreate(
        product_id=product.id, seller_id=seller.id, buyer_name="U", rating=2, comment="Bad"
    ))
    updated = await service.update(review.id, ReviewUpdate(rating=4, comment="Updated"))
    assert updated.rating == 4
    assert updated.comment == "Updated"


@pytest.mark.asyncio
async def test_delete_review(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="DelRev", email="dr@test.com")
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="DelItem", price=5, stock=5
    ))
    service = ReviewService(db=db_session)
    review = await service.create(ReviewCreate(
        product_id=product.id, seller_id=seller.id, buyer_name="X", rating=3
    ))
    await service.delete(review.id)
    with pytest.raises(ReviewNotFoundError):
        await service.get_by_id(review.id)
