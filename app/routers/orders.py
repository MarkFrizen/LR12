"""REST-эндпоинты для заказов."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import OrderCreate, OrderResponse, OrderUpdate
from app.services.order_service import OrderService

router = APIRouter(prefix="/api/v1/orders", tags=["Заказы"])


async def get_order_service(db: AsyncSession = Depends(get_db)) -> OrderService:
    return OrderService(db=db)


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    service: OrderService = Depends(get_order_service),
):
    return await service.create(data)


@router.get("/", response_model=list[OrderResponse])
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    seller_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    service: OrderService = Depends(get_order_service),
):
    return await service.get_all(
        skip=skip, limit=limit, seller_id=seller_id, status=status_filter
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    return await service.get_by_id(order_id)


@router.patch("/{order_id}", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    data: OrderUpdate,
    service: OrderService = Depends(get_order_service),
):
    return await service.update_status(order_id, data)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
):
    await service.delete(order_id)
