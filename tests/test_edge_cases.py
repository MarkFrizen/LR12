"""
Модульные тесты граничных случаев.

Покрытие:
- Цена товара: 0.01, отрицательная, None
- Пустой список заказов
- Несуществующий продавец (заказ, комиссия, отзыв)
- Несуществующий товар (заказ, отзыв)
- Комиссия с нулевой суммой
- Отзыв без оценки
"""

import pytest
from decimal import Decimal

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import patch

from app.exceptions import (
    ProductNotFoundError,
    SellerNotFoundError,
    OrderNotFoundError,
)
from app.models.commission import CommissionCreate
from app.models.order import OrderCreate
from app.models.product import ProductCreate
from app.models.review import ReviewCreate
from app.models.seller import SellerCreate
from app.services.commission_service import CommissionService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.review_service import ReviewService
from app.services.seller_service import SellerService


_TEST_USER_ID = 1
_TEST_MOD_ROLE = "admin"
_TEST_BUYER = "test_buyer"


# ═══════════════════════════════════════════════════════════
# Цена товара: граничные значения
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_product_price_edge_001(db_session: AsyncSession):
    """Цена товара 0.01 — минимальное допустимое значение (gt=0) проходит."""
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="EdgeSeller", email="edge001@test.com"),
        user_id=_TEST_USER_ID,
    )
    service = ProductService(db=db_session)
    product = await service.create(ProductCreate(
        seller_id=seller.id,
        name="CheapItem",
        price=Decimal("0.01"),
        stock=1,
    ), user_id=_TEST_USER_ID)
    assert product.id is not None
    assert product.price == Decimal("0.01")


@pytest.mark.asyncio
async def test_product_negative_price_rejected():
    """Отрицательная цена отклоняется Pydantic-валидацией (gt=0)."""
    with pytest.raises(ValidationError):
        ProductCreate(
            seller_id=1,
            name="Negative",
            price=Decimal("-10.00"),
            stock=1,
        )


@pytest.mark.asyncio
async def test_product_price_none_rejected():
    """None вместо цены отклоняется Pydantic-валидацией (обязательное поле)."""
    with pytest.raises(ValidationError):
        ProductCreate(
            seller_id=1,
            name="NoPrice",
            price=None,  # type: ignore[arg-type]
            stock=1,
        )


# ═══════════════════════════════════════════════════════════
# Пустой список заказов
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_orders_empty_list(db_session: AsyncSession):
    """get_all() возвращает пустой список, когда заказов нет."""
    service = OrderService(db=db_session)
    orders = await service.get_all()
    assert orders == []


# ═══════════════════════════════════════════════════════════
# Несуществующий продавец
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_order_nonexistent_seller(db_session: AsyncSession):
    """Создание заказа у несуществующего продавца → SellerNotFoundError."""
    service = OrderService(db=db_session)
    with pytest.raises(SellerNotFoundError):
        await service.create(
            OrderCreate(product_id=1, seller_id=999, quantity=1),
            buyer_username=_TEST_BUYER,
        )


@pytest.mark.asyncio
async def test_commission_nonexistent_seller(db_session: AsyncSession):
    """Создание комиссии у несуществующего продавца → SellerNotFoundError."""
    service = CommissionService(db=db_session)
    with pytest.raises(SellerNotFoundError):
        with patch("app.services.commission_service.logger") as mock_logger:
            await service.create(CommissionCreate(
                order_id=1,
                seller_id=999,
                amount=Decimal("10"),
                percentage=Decimal("10.00"),
            ))
        mock_logger.warning.assert_called_once_with(
            "Попытка создать комиссию у несуществующего продавца id=%d", 999
        )


@pytest.mark.asyncio
async def test_review_nonexistent_seller(db_session: AsyncSession):
    """Создание отзыва у несуществующего продавца → SellerNotFoundError."""
    service = ReviewService(db=db_session)
    with pytest.raises(SellerNotFoundError):
        await service.create(
            ReviewCreate(product_id=1, seller_id=999, rating=5),
            buyer_username=_TEST_BUYER,
        )


# ═══════════════════════════════════════════════════════════
# Несуществующий товар
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_order_nonexistent_product(db_session: AsyncSession):
    """Создание заказа на несуществующий товар → ProductNotFoundError."""
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="ProdSeller", email="prod@test.com"),
        user_id=_TEST_USER_ID,
    )
    service = OrderService(db=db_session)
    with pytest.raises(ProductNotFoundError):
        await service.create(
            OrderCreate(product_id=999, seller_id=seller.id, quantity=1),
            buyer_username=_TEST_BUYER,
        )


@pytest.mark.asyncio
async def test_review_nonexistent_product(db_session: AsyncSession):
    """Создание отзыва на несуществующий товар → ProductNotFoundError."""
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="RevSeller", email="rev@test.com"),
        user_id=_TEST_USER_ID,
    )
    service = ReviewService(db=db_session)
    with pytest.raises(ProductNotFoundError):
        await service.create(
            ReviewCreate(product_id=999, seller_id=seller.id, rating=5),
            buyer_username=_TEST_BUYER,
        )


# ═══════════════════════════════════════════════════════════
# Комиссия при нулевой сумме заказа
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_commission_zero_amount_rejected():
    """Комиссия с amount=0 отклоняется Pydantic-валидацией (gt=0)."""
    with pytest.raises(ValidationError):
        CommissionCreate(
            order_id=1,
            seller_id=1,
            amount=Decimal("0.00"),
            percentage=Decimal("10.00"),
        )


@pytest.mark.asyncio
async def test_commission_minimal_amount(db_session: AsyncSession):
    """Комиссия с amount=0.01 — минимально допустимое значение проходит."""
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="ComSeller", email="com001@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="ComItem", price=100, stock=10
    ), user_id=_TEST_USER_ID)
    order = await OrderService(db=db_session).create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=1),
        buyer_username=_TEST_BUYER,
    )
    service = CommissionService(db=db_session)
    commission = await service.create(CommissionCreate(
        order_id=order.id,
        seller_id=seller.id,
        amount=Decimal("0.01"),
        percentage=Decimal("1.00"),
    ))
    assert commission.id is not None
    assert commission.amount == Decimal("0.01")


# ═══════════════════════════════════════════════════════════
# Отзыв без оценки
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_review_without_rating_rejected():
    """Отзыв с rating=None отклоняется Pydantic-валидацией (обязательное поле)."""
    with pytest.raises(ValidationError):
        ReviewCreate(
            product_id=1,
            seller_id=1,
            rating=None,  # type: ignore[arg-type]
            comment="No rating",
        )


@pytest.mark.asyncio
async def test_review_rating_below_min_rejected():
    """Отзыв с rating=0 отклоняется Pydantic-валидацией (ge=1)."""
    with pytest.raises(ValidationError):
        ReviewCreate(
            product_id=1,
            seller_id=1,
            rating=0,
            comment="Below minimum",
        )


@pytest.mark.asyncio
async def test_review_rating_above_max_rejected():
    """Отзыв с rating=6 отклоняется Pydantic-валидацией (le=5)."""
    with pytest.raises(ValidationError):
        ReviewCreate(
            product_id=1,
            seller_id=1,
            rating=6,
            comment="Above maximum",
        )


# ═══════════════════════════════════════════════════════════
# Несуществующий заказ (для комиссии)
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_commission_nonexistent_order(db_session: AsyncSession):
    """Создание комиссии для несуществующего заказа → OrderNotFoundError."""
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="ComOrderSeller", email="co@test.com"),
        user_id=_TEST_USER_ID,
    )
    service = CommissionService(db=db_session)
    with pytest.raises(OrderNotFoundError):
        await service.create(CommissionCreate(
            order_id=999,
            seller_id=seller.id,
            amount=Decimal("10"),
            percentage=Decimal("10.00"),
        ))
