"""
Тесты сервиса продавцов.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import SellerNotFoundError, DuplicateEmailError
from app.models.seller import SellerCreate, SellerUpdate
from app.services.seller_service import SellerService


@pytest.mark.asyncio
async def test_create_seller(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(SellerCreate(name="Test Seller", email="seller@test.com"))
    assert seller.id is not None
    assert seller.name == "Test Seller"
    assert seller.email == "seller@test.com"


@pytest.mark.asyncio
async def test_create_duplicate_email(db_session: AsyncSession):
    service = SellerService(db=db_session)
    await service.create(SellerCreate(name="A", email="dup@test.com"))
    with pytest.raises(DuplicateEmailError):
        await service.create(SellerCreate(name="B", email="dup@test.com"))


@pytest.mark.asyncio
async def test_get_seller_by_id(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(SellerCreate(name="GetTest", email="get@test.com"))
    found = await service.get_by_id(seller.id)
    assert found.id == seller.id
    assert found.name == "GetTest"


@pytest.mark.asyncio
async def test_get_seller_not_found(db_session: AsyncSession):
    service = SellerService(db=db_session)
    with pytest.raises(SellerNotFoundError):
        await service.get_by_id(999)


@pytest.mark.asyncio
async def test_get_all_sellers(db_session: AsyncSession):
    service = SellerService(db=db_session)
    await service.create(SellerCreate(name="S1", email="s1@test.com"))
    await service.create(SellerCreate(name="S2", email="s2@test.com"))
    sellers = await service.get_all()
    assert len(sellers) >= 2


@pytest.mark.asyncio
async def test_update_seller(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(SellerCreate(name="OldName", email="old@test.com"))
    updated = await service.update(seller.id, SellerUpdate(name="NewName", rating=4.5))
    assert updated.name == "NewName"
    assert updated.rating == 4.5


@pytest.mark.asyncio
async def test_delete_seller(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(SellerCreate(name="DelMe", email="del@test.com"))
    await service.delete(seller.id)
    with pytest.raises(SellerNotFoundError):
        await service.get_by_id(seller.id)
