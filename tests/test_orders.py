"""
Тесты сервиса заказов.

Покрытие: создание заказа, проверка остатка, обновление статуса,
удаление, обработка InsufficientStock и NotFound.
"""

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import InsufficientStockError, OrderNotFoundError
from app.models.order import OrderCreate, OrderUpdate, OrderStatus
from app.models.product import ProductCreate
from app.models.seller import SellerCreate
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.seller_service import SellerService


_TEST_USER_ID = 1
_TEST_MOD_ROLE = "admin"
_TEST_BUYER = "test_buyer"


@pytest.mark.asyncio
async def test_create_order(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="OrdSeller", email="ord@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="Item", price=Decimal("100"), stock=10
    ), user_id=_TEST_USER_ID)
    service = OrderService(db=db_session)
    order = await service.create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=2),
        buyer_username=_TEST_BUYER,
    )
    assert order.id is not None
    assert order.total_price == Decimal("200")
    assert order.status == OrderStatus.PENDING.value
    assert order.buyer_name == _TEST_BUYER


@pytest.mark.asyncio
async def test_create_order_insufficient_stock(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="LowStock", email="low@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="Rare", price=Decimal("1000"), stock=1
    ), user_id=_TEST_USER_ID)
    service = OrderService(db=db_session)
    with pytest.raises(InsufficientStockError):
        await service.create(
            OrderCreate(product_id=product.id, seller_id=seller.id, quantity=5),
            buyer_username=_TEST_BUYER,
        )


@pytest.mark.asyncio
async def test_order_updates_stock(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="StockTest", email="st@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="Widget", price=Decimal("50"), stock=10
    ), user_id=_TEST_USER_ID)
    service = OrderService(db=db_session)
    await service.create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=3),
        buyer_username="Bob",
    )
    updated_product = await ProductService(db=db_session).get_by_id(product.id)
    assert updated_product.stock == 7  # 10 - 3 = 7


@pytest.mark.asyncio
async def test_update_order_status(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="StatusTest", email="status@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="ShipMe", price=Decimal("30"), stock=5
    ), user_id=_TEST_USER_ID)
    service = OrderService(db=db_session)
    order = await service.create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=1),
        buyer_username="Alice",
    )
    updated = await service.update_status(
        order.id, OrderUpdate(status=OrderStatus.SHIPPED),
        user_id=_TEST_USER_ID, user_role=_TEST_MOD_ROLE,
    )
    assert updated.status == OrderStatus.SHIPPED.value


@pytest.mark.asyncio
async def test_delete_order(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="DelOrder", email="do@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="DelItem", price=Decimal("10"), stock=5
    ), user_id=_TEST_USER_ID)
    service = OrderService(db=db_session)
    order = await service.create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=1),
        buyer_username="X",
    )
    await service.delete(order.id)
    with pytest.raises(OrderNotFoundError):
        await service.get_by_id(order.id)
