"""
Сервис аналитики и отчётов для маркетплейса.

Предоставляет агрегированные данные:
- Общий оборот (сумма заказов)
- Средний чек
- Топ товаров по количеству заказов
- Сводка по комиссиям
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.logger import get_logger
from app.models.commission import CommissionORM
from app.models.order import OrderORM
from app.models.product import ProductORM

logger = get_logger(__name__)


# ───────────────────────────── Pydantic схемы ответов ─────────────────────────────

class RevenueResponse(BaseModel):
    """Ответ: оборот."""

    total_revenue: Decimal = Field(..., decimal_places=2, description="Общий оборот")
    orders_count: int = Field(..., description="Количество заказов")
    currency: str = "RUB"


class AvgOrderValueResponse(BaseModel):
    """Ответ: средний чек."""

    avg_order_value: Decimal = Field(..., decimal_places=2, description="Средний чек")
    orders_count: int = Field(..., description="Количество заказов")
    currency: str = "RUB"


class TopProductItem(BaseModel):
    """Элемент топа товаров."""

    product_id: int
    product_name: str
    orders_count: int
    total_revenue: Decimal
    category: Optional[str] = None


class TopProductsResponse(BaseModel):
    """Ответ: топ товаров."""

    products: list[TopProductItem]


class CommissionsSummaryResponse(BaseModel):
    """Ответ: сводка по комиссиям."""

    total_paid: Decimal = Field(..., decimal_places=2, description="Выплачено")
    total_pending: Decimal = Field(..., decimal_places=2, description="Ожидает выплаты")
    total_refunded: Decimal = Field(..., decimal_places=2, description="Возвращено")
    commissions_count: int = Field(..., description="Всего комиссий")
    currency: str = "RUB"


class DashboardSummaryResponse(BaseModel):
    """Ответ: сводка для dashboard."""

    total_revenue: Decimal = Field(..., decimal_places=2)
    avg_order_value: Decimal = Field(..., decimal_places=2)
    orders_count: int
    top_products: list[TopProductItem]
    commissions: CommissionsSummaryResponse


# ───────────────────────────── Сервис ─────────────────────────────

class AnalyticsService:
    """Сервис для получения аналитических данных."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_revenue(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> RevenueResponse:
        """
        Рассчитать общий оборот (сумма total_price всех заказов).

        Args:
            start_date: Начало периода (опционально).
            end_date: Конец периода (опционально).

        Returns:
            RevenueResponse.
        """
        query = select(
            func.coalesce(func.sum(OrderORM.total_price), 0),
            func.count(OrderORM.id),
        )

        if start_date:
            query = query.where(OrderORM.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.where(OrderORM.created_at <= datetime.combine(end_date, datetime.max.time()))

        result = await self.db.execute(query)
        row = result.one()
        total = Decimal(str(row[0])).quantize(Decimal("0.01"))
        count = int(row[1])

        logger.debug("Аналитика: оборот=%s, заказов=%d", total, count)
        return RevenueResponse(total_revenue=total, orders_count=count)

    async def get_avg_order_value(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> AvgOrderValueResponse:
        """
        Рассчитать средний чек.

        Args:
            start_date: Начало периода (опционально).
            end_date: Конец периода (опционально).

        Returns:
            AvgOrderValueResponse.
        """
        query = select(
            func.coalesce(func.avg(OrderORM.total_price), 0),
            func.count(OrderORM.id),
        )

        if start_date:
            query = query.where(OrderORM.created_at >= datetime.combine(start_date, datetime.min.time()))
        if end_date:
            query = query.where(OrderORM.created_at <= datetime.combine(end_date, datetime.max.time()))

        result = await self.db.execute(query)
        row = result.one()
        avg = Decimal(str(row[0])).quantize(Decimal("0.01"))
        count = int(row[1])

        logger.debug("Аналитика: средний чек=%s, заказов=%d", avg, count)
        return AvgOrderValueResponse(avg_order_value=avg, orders_count=count)

    async def get_top_products(self, limit: int = 10) -> TopProductsResponse:
        """
        Получить топ товаров по количеству заказов.

        Args:
            limit: Максимальное количество товаров.

        Returns:
            TopProductsResponse.
        """
        # SQLite округляет Numeric — используем CAST для переносимости
        query = (
            select(
                ProductORM.id,
                ProductORM.name,
                ProductORM.category,
                func.count(OrderORM.id).label("orders_count"),
                func.coalesce(func.sum(OrderORM.total_price), 0).label("total_revenue"),
            )
            .join(OrderORM, OrderORM.product_id == ProductORM.id, isouter=True)
            .group_by(ProductORM.id)
            .order_by(func.count(OrderORM.id).desc())
            .limit(limit)
        )

        result = await self.db.execute(query)
        rows = result.all()

        products = [
            TopProductItem(
                product_id=row.id,
                product_name=row.name,
                orders_count=int(row.orders_count),
                total_revenue=Decimal(str(row.total_revenue)).quantize(Decimal("0.01")),
                category=row.category,
            )
            for row in rows
        ]

        logger.debug("Аналитика: топ-%d товаров", limit)
        return TopProductsResponse(products=products)

    async def get_commissions_summary(self) -> CommissionsSummaryResponse:
        """
        Получить сводку по комиссиям (paid, pending, refunded).

        Returns:
            CommissionsSummaryResponse.
        """
        # Суммы по статусам
        paid_subq = (
            select(func.coalesce(func.sum(CommissionORM.amount), 0))
            .where(CommissionORM.status == "paid")
            .scalar_subquery()
        )
        pending_subq = (
            select(func.coalesce(func.sum(CommissionORM.amount), 0))
            .where(CommissionORM.status == "pending")
            .scalar_subquery()
        )
        refunded_subq = (
            select(func.coalesce(func.sum(CommissionORM.amount), 0))
            .where(CommissionORM.status == "refunded")
            .scalar_subquery()
        )
        count_subq = (
            select(func.count(CommissionORM.id))
            .scalar_subquery()
        )

        query = select(paid_subq, pending_subq, refunded_subq, count_subq)
        result = await self.db.execute(query)
        row = result.one()

        summary = CommissionsSummaryResponse(
            total_paid=Decimal(str(row[0])).quantize(Decimal("0.01")),
            total_pending=Decimal(str(row[1])).quantize(Decimal("0.01")),
            total_refunded=Decimal(str(row[2])).quantize(Decimal("0.01")),
            commissions_count=int(row[3]),
        )

        logger.debug(
            "Аналитика: комиссии — paid=%s, pending=%s, refunded=%s",
            summary.total_paid, summary.total_pending, summary.total_refunded,
        )
        return summary

    async def get_dashboard_summary(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        top_limit: int = 5,
    ) -> DashboardSummaryResponse:
        """
        Получить сводку для главной панели dashboard.

        Args:
            start_date: Начало периода (опционально).
            end_date: Конец периода (опционально).
            top_limit: Количество товаров в топе.

        Returns:
            DashboardSummaryResponse.
        """
        revenue = await self.get_revenue(start_date, end_date)
        avg_order = await self.get_avg_order_value(start_date, end_date)
        top_products = await self.get_top_products(limit=top_limit)
        commissions = await self.get_commissions_summary()

        return DashboardSummaryResponse(
            total_revenue=revenue.total_revenue,
            avg_order_value=avg_order.avg_order_value,
            orders_count=revenue.orders_count,
            top_products=top_products.products,
            commissions=commissions,
        )
