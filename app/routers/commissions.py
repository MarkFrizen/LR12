"""
REST-эндпоинты для комиссий.

Защита по ролям:
    - POST   / — только admin
    - GET    / — admin, moderator
    - GET    /{id} — admin, moderator
    - PATCH  /{id} — только admin
    - DELETE /{id} — только admin
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_admin, require_moderator
from app.auth.models import UserORM
from app.database import get_db
from app.models.commission import CommissionCreate, CommissionResponse, CommissionUpdate
from app.services.commission_service import CommissionService

router = APIRouter(prefix="/api/v1/commissions", tags=["Комиссии"])


async def get_commission_service(
    db: AsyncSession = Depends(get_db),
) -> CommissionService:
    """Фабрика сервиса комиссий."""
    return CommissionService(db=db)


@router.post("/", response_model=CommissionResponse, status_code=status.HTTP_201_CREATED)
async def create_commission(
    data: CommissionCreate,
    service: CommissionService = Depends(get_commission_service),
    _admin: UserORM = Depends(require_admin),
):
    """Создать комиссию (только admin)."""
    return await service.create(data)


@router.get("/", response_model=list[CommissionResponse])
async def list_commissions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    seller_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    service: CommissionService = Depends(get_commission_service),
    current_user: UserORM = Depends(get_current_user),
):
    """Получить список комиссий."""
    return await service.get_all(
        skip=skip, limit=limit, seller_id=seller_id, status=status_filter
    )


@router.get("/{commission_id}", response_model=CommissionResponse)
async def get_commission(
    commission_id: int,
    service: CommissionService = Depends(get_commission_service),
    current_user: UserORM = Depends(get_current_user),
):
    """Получить комиссию по ID."""
    return await service.get_by_id(commission_id)


@router.patch("/{commission_id}", response_model=CommissionResponse)
async def update_commission(
    commission_id: int,
    data: CommissionUpdate,
    service: CommissionService = Depends(get_commission_service),
    _admin: UserORM = Depends(require_admin),
):
    """Обновить комиссию (только admin)."""
    return await service.update(commission_id, data)


@router.delete("/{commission_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_commission(
    commission_id: int,
    service: CommissionService = Depends(get_commission_service),
    _admin: UserORM = Depends(require_admin),
):
    """Удалить комиссию (только admin)."""
    await service.delete(commission_id)
