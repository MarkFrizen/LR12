"""
Тесты сервиса товаров.
"""

import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import ProductNotFoundError, SellerNotFoundError
from app.models.product import ProductCreate, ProductUpdate
from app.models.seller import SellerCreate
from app.services.product_service import ProductService
from app.services.seller_service import SellerService


@pytest.mark.asyncio
async def test_create_product(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="ProdSeller", email="prod@test.com")
    )
    service = ProductService(db=db_session)
    product = await service.create(ProductCreate(
        seller_id=seller.id, name="Laptop", price=Decimal("999.99"), stock=10
    ))
    assert product.id is not None
    assert product.name == "Laptop"
    assert product.price == Decimal("999.99")


@pytest.mark.asyncio
async def test_create_product_invalid_seller(db_session: AsyncSession):
    service = ProductService(db=db_session)
    with pytest.raises(SellerNotFoundError):
        await service.create(ProductCreate(
            seller_id=999, name="Ghost", price=Decimal("100"), stock=1
        ))


@pytest.mark.asyncio
async def test_get_product_by_id(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="GSeller", email="gs@test.com")
    )
    service = ProductService(db=db_session)
    product = await service.create(ProductCreate(
        seller_id=seller.id, name="Phone", price=Decimal("500"), stock=5
    ))
    found = await service.get_by_id(product.id)
    assert found.name == "Phone"


@pytest.mark.asyncio
async def test_get_product_not_found(db_session: AsyncSession):
    service = ProductService(db=db_session)
    with pytest.raises(ProductNotFoundError):
        await service.get_by_id(999)


@pytest.mark.asyncio
async def test_update_product(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="UpdSeller", email="us@test.com")
    )
    service = ProductService(db=db_session)
    product = await service.create(ProductCreate(
        seller_id=seller.id, name="Old", price=Decimal("100"), stock=5
    ))
    updated = await service.update(product.id, ProductUpdate(name="New", price=Decimal("200")))
    assert updated.name == "New"
    assert updated.price == Decimal("200")


@pytest.mark.asyncio
async def test_delete_product(db_session: AsyncSession):
    seller = await SellerService(db=db_session).create(
        SellerCreate(name="DelSeller", email="ds@test.com")
    )
    service = ProductService(db=db_session)
    product = await service.create(ProductCreate(
        seller_id=seller.id, name="DelMe", price=Decimal("50"), stock=2
    ))
    await service.delete(product.id)
    with pytest.raises(ProductNotFoundError):
        await service.get_by_id(product.id)
