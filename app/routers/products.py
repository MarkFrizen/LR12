"""REST-эндпоинты для товаров."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Товары"])


async def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(db=db)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),
):
    return await service.create(data)


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    seller_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    service: ProductService = Depends(get_product_service),
):
    return await service.get_all(
        skip=skip, limit=limit, seller_id=seller_id, category=category
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    return await service.get_by_id(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
):
    return await service.update(product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    await service.delete(product_id)
