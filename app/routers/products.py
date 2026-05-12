"""
REST-эндпоинты для товаров.

Защита по ролям:
    - POST   / — только seller, admin, moderator  (require_seller)
    - GET    / — любой аутентифицированный пользователь
    - GET    /{id} — любой аутентифицированный пользователь
    - PATCH  /{id} — только seller (владелец), admin, moderator
    - DELETE /{id} — только admin
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_seller
from app.auth.models import UserORM
from app.database import get_db
from app.models.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.product_service import ProductService

router = APIRouter(prefix="/api/v1/products", tags=["Товары"])


async def get_product_service(db: AsyncSession = Depends(get_db)) -> ProductService:
    """Фабрика сервиса товаров."""
    return ProductService(db=db)


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    service: ProductService = Depends(get_product_service),
    current_user: UserORM = Depends(require_seller),
):
    """
    Создать новый товар.

    Доступно: продавцам, модераторам, администраторам.
    """
    return await service.create(data, user_id=current_user.id)


@router.get("/", response_model=list[ProductResponse])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    seller_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    service: ProductService = Depends(get_product_service),
):
    """Получить список товаров (публичный доступ)."""
    return await service.get_all(
        skip=skip, limit=limit, seller_id=seller_id, category=category
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
):
    """Получить товар по ID (публичный доступ)."""
    return await service.get_by_id(product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    data: ProductUpdate,
    service: ProductService = Depends(get_product_service),
    current_user: UserORM = Depends(require_seller),
):
    """
    Обновить товар.

    Доступно: продавец (только свои товары), модератор, администратор.
    """
    return await service.update(product_id, data, user_id=current_user.id, user_role=current_user.role)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service),
    _admin: UserORM = Depends(require_admin),
):
    """
    Удалить товар.

    Доступно: только администратор.
    """
    await service.delete(product_id)
