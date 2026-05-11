"""
REST-эндпоинты для продавцов.

SRP: только маршрутизация HTTP, бизнес-логика в SellerService.
ISP: зависимости только через Depends.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.seller import SellerCreate, SellerResponse, SellerUpdate
from app.services.seller_service import SellerService

router = APIRouter(prefix="/api/v1/sellers", tags=["Продавцы"])


async def get_seller_service(db: AsyncSession = Depends(get_db)) -> SellerService:
    """Фабрика сервиса — DIP (зависимость от абстракции AsyncSession)."""
    return SellerService(db=db)


@router.post("/", response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def create_seller(
    data: SellerCreate,
    service: SellerService = Depends(get_seller_service),
):
    """Создать нового продавца."""
    return await service.create(data)


@router.get("/", response_model=list[SellerResponse])
async def list_sellers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: SellerService = Depends(get_seller_service),
):
    """Список продавцов."""
    return await service.get_all(skip=skip, limit=limit)


@router.get("/{seller_id}", response_model=SellerResponse)
async def get_seller(
    seller_id: int,
    service: SellerService = Depends(get_seller_service),
):
    """Продавец по ID."""
    return await service.get_by_id(seller_id)


@router.patch("/{seller_id}", response_model=SellerResponse)
async def update_seller(
    seller_id: int,
    data: SellerUpdate,
    service: SellerService = Depends(get_seller_service),
):
    """Обновить продавца."""
    return await service.update(seller_id, data)


@router.delete("/{seller_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_seller(
    seller_id: int,
    service: SellerService = Depends(get_seller_service),
):
    """Удалить продавца."""
    await service.delete(seller_id)
