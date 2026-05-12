"""
Тесты сервиса продавцов.

Покрытие: CRUD-операции, уникальность email, обработка NotFound.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions import SellerNotFoundError, DuplicateEmailError
from app.models.seller import SellerCreate, SellerUpdate
from app.services.seller_service import SellerService


_TEST_USER_ID = 1
_TEST_MOD_ROLE = "admin"


@pytest.mark.asyncio
async def test_create_seller(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(
        SellerCreate(name="Test Seller", email="seller@test.com"),
        user_id=_TEST_USER_ID,
    )
    assert seller.id is not None
    assert seller.name == "Test Seller"
    assert seller.email == "seller@test.com"


@pytest.mark.asyncio
async def test_create_duplicate_email(db_session: AsyncSession):
    service = SellerService(db=db_session)
    await service.create(SellerCreate(name="A", email="dup@test.com"), user_id=_TEST_USER_ID)
    with pytest.raises(DuplicateEmailError):
        await service.create(SellerCreate(name="B", email="dup@test.com"), user_id=_TEST_USER_ID)


@pytest.mark.asyncio
async def test_get_seller_by_id(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(
        SellerCreate(name="GetTest", email="get@test.com"),
        user_id=_TEST_USER_ID,
    )
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
    await service.create(SellerCreate(name="S1", email="s1@test.com"), user_id=_TEST_USER_ID)
    await service.create(SellerCreate(name="S2", email="s2@test.com"), user_id=_TEST_USER_ID)
    sellers = await service.get_all()
    assert len(sellers) >= 2


@pytest.mark.asyncio
async def test_update_seller(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(
        SellerCreate(name="OldName", email="old@test.com"),
        user_id=_TEST_USER_ID,
    )
    updated = await service.update(
        seller.id, SellerUpdate(name="NewName"),
        user_id=_TEST_USER_ID, user_role=_TEST_MOD_ROLE,
    )
    assert updated.name == "NewName"


@pytest.mark.asyncio
async def test_delete_seller(db_session: AsyncSession):
    service = SellerService(db=db_session)
    seller = await service.create(
        SellerCreate(name="DelMe", email="del@test.com"),
        user_id=_TEST_USER_ID,
    )
    await service.delete(seller.id)
    with pytest.raises(SellerNotFoundError):
        await service.get_by_id(seller.id)
