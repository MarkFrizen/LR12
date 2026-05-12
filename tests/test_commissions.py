"""
Тесты сервиса комиссий.

Покрытие: создание, чтение, обновление статуса, удаление комиссий,
обработка CommissionNotFound.
"""

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import CommissionNotFoundError
from app.models.commission import CommissionCreate, CommissionUpdate
from app.models.order import OrderCreate
from app.models.product import ProductCreate
from app.models.seller import SellerCreate
from app.services.commission_service import CommissionService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.seller_service import SellerService


_TEST_USER_ID = 1
_TEST_BUYER = "buyer"


@pytest.mark.asyncio
async def test_create_commission(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="ComSeller", email="com@test.com"),
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
        amount=Decimal("10"),
        percentage=Decimal("10.00"),
    ))
    assert commission.id is not None
    assert commission.amount == Decimal("10")
    assert commission.status == "pending"


@pytest.mark.asyncio
async def test_get_commission_by_id(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="GetCom", email="gc@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="GetComItem", price=100, stock=10
    ), user_id=_TEST_USER_ID)
    order = await OrderService(db=db_session).create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=1),
        buyer_username=_TEST_BUYER,
    )
    service = CommissionService(db=db_session)
    commission = await service.create(CommissionCreate(
        order_id=order.id, seller_id=seller.id, amount=Decimal("5"), percentage=Decimal("5")
    ))
    found = await service.get_by_id(commission.id)
    assert found.id == commission.id


@pytest.mark.asyncio
async def test_update_commission_status(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="UpdCom", email="uc@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="UpdComItem", price=200, stock=5
    ), user_id=_TEST_USER_ID)
    order = await OrderService(db=db_session).create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=1),
        buyer_username=_TEST_BUYER,
    )
    service = CommissionService(db=db_session)
    commission = await service.create(CommissionCreate(
        order_id=order.id, seller_id=seller.id, amount=Decimal("20"), percentage=Decimal("10")
    ))
    updated = await service.update(commission.id, CommissionUpdate(status="paid"))
    assert updated.status == "paid"


@pytest.mark.asyncio
async def test_delete_commission(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="DelCom", email="dc@test.com"),
        user_id=_TEST_USER_ID,
    )
    product = await ProductService(db=db_session).create(ProductCreate(
        seller_id=seller.id, name="DelComItem", price=50, stock=5
    ), user_id=_TEST_USER_ID)
    order = await OrderService(db=db_session).create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=1),
        buyer_username=_TEST_BUYER,
    )
    service = CommissionService(db=db_session)
    commission = await service.create(CommissionCreate(
        order_id=order.id, seller_id=seller.id, amount=Decimal("5"), percentage=Decimal("10")
    ))
    await service.delete(commission.id)
    with pytest.raises(CommissionNotFoundError):
        await service.get_by_id(commission.id)
