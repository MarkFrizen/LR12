"""
REST-эндпоинты для аналитики и отчётов.

Предоставляет агрегированные данные:
- Оборот и средний чек
- Топ товаров
- Сводка по комиссиям
- Полная сводка для dashboard

Доступно: администраторам и модераторам.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_moderator
from app.auth.models import UserORM
from app.database import get_db
from app.services.analytics_service import (
    AnalyticsService,
    AvgOrderValueResponse,
    CommissionsSummaryResponse,
    DashboardSummaryResponse,
    RevenueResponse,
    TopProductsResponse,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Аналитика"])


async def get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    """Фабрика сервиса аналитики."""
    return AnalyticsService(db=db)


@router.get("/revenue", response_model=RevenueResponse)
async def get_revenue(
    start_date: Optional[date] = Query(None, description="Начало периода (ГГГГ-ММ-ДД)"),
    end_date: Optional[date] = Query(None, description="Конец периода (ГГГГ-ММ-ДД)"),
    service: AnalyticsService = Depends(get_analytics_service),
    _admin: UserORM = Depends(require_moderator),
):
    """Общий оборот за период (сумма всех заказов)."""
    return await service.get_revenue(start_date, end_date)


@router.get("/avg-order-value", response_model=AvgOrderValueResponse)
async def get_avg_order_value(
    start_date: Optional[date] = Query(None, description="Начало периода (ГГГГ-ММ-ДД)"),
    end_date: Optional[date] = Query(None, description="Конец периода (ГГГГ-ММ-ДД)"),
    service: AnalyticsService = Depends(get_analytics_service),
    _admin: UserORM = Depends(require_moderator),
):
    """Средний чек за период."""
    return await service.get_avg_order_value(start_date, end_date)


@router.get("/top-products", response_model=TopProductsResponse)
async def get_top_products(
    limit: int = Query(10, ge=1, le=100, description="Количество товаров"),
    service: AnalyticsService = Depends(get_analytics_service),
    _admin: UserORM = Depends(require_moderator),
):
    """Топ товаров по количеству заказов."""
    return await service.get_top_products(limit=limit)


@router.get("/commissions-summary", response_model=CommissionsSummaryResponse)
async def get_commissions_summary(
    service: AnalyticsService = Depends(get_analytics_service),
    _admin: UserORM = Depends(require_moderator),
):
    """Сводка по комиссиям (выплачено / ожидает / возвращено)."""
    return await service.get_commissions_summary()


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    top_limit: int = Query(5, ge=1, le=50, description="Количество товаров в топе"),
    service: AnalyticsService = Depends(get_analytics_service),
    _admin: UserORM = Depends(require_moderator),
):
    """Полная сводка для dashboard: оборот, средний чек, топ товаров, комиссии."""
    return await service.get_dashboard_summary(top_limit=top_limit)
