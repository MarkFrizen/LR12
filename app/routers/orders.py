"""
REST-эндпоинты для заказов.

Защита по ролям:
    - POST   / — только buyer, admin  (require_buyer)
    - GET    / — любой аутентифицированный
    - GET    /{id} — любой аутентифицированный
    - PATCH  /{id} — seller (продавец заказа), admin, moderator
    - DELETE /{id} — только admin
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_buyer, require_moderator
from app.auth.models import UserORM
from app.database import get_db
from app.models.order import OrderCreate, OrderResponse, OrderUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["Заказы"])


async def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    """Фабрика сервиса заказов."""
    return OrderService(db=db)


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    service: OrderService = Depends(get_order_service),
    current_user: UserORM = Depends(require_buyer),
):
    """
    Создать новый заказ.

    Доступно: покупателям и администраторам.
    buyer_name устанавливается автоматически из учётной записи.
    """
    return await service.create(data, buyer_username=current_user.username)


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    seller_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    service: OrderService = Depends(get_order_service),
    current_user: UserORM = Depends(get_current_user),
):
    """Получить список заказов."""
    return await service.get_all(
        skip=skip, limit=limit, seller_id=seller_id, status=status_filter
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
    current_user: UserORM = Depends(get_current_user),
):
    """Получить заказ по ID."""
    return await service.get_by_id(order_id)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    data: OrderUpdate,
    service: OrderService = Depends(get_order_service),
    current_user: UserORM = Depends(require_moderator),
):
    """
    Обновить статус заказа.

    Доступно: модераторам и администраторам.
    """
    return await service.update_status(order_id, data, user_id=current_user.id, user_role=current_user.role)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
    _admin: UserORM = Depends(require_admin),
):
    """Удалить заказ (только admin)."""
    await service.delete(order_id)
