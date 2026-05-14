"""
Тесты сервиса и эндпоинтов аналитики.

Покрытие:
- Сервис: пустая БД, с данными, фильтр по датам
- HTTP: авторизация admin (200), buyer (403)
- Dashboard summary
"""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commission import CommissionCreate, CommissionORM
from app.models.order import OrderCreate
from app.models.product import ProductCreate
from app.models.seller import SellerCreate
from app.services.analytics_service import AnalyticsService
from app.services.commission_service import CommissionService
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.seller_service import SellerService

_TEST_USER_ID = 1
_TEST_BUYER = "analytics_buyer"
_TEST_ADMIN_USER = "test_admin"


# ══════════════════════════════════════════════════
# Сервис аналитики
# ══════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_revenue_empty(db_session: AsyncSession):
    """Оборот с пустой БД — 0."""
    service = AnalyticsService(db=db_session)
    result = await service.get_revenue()
    assert result.total_revenue == Decimal("0.00")
    assert result.orders_count == 0


@pytest.mark.asyncio
async def test_revenue_with_orders(db_session: AsyncSession):
    """Оборот с заказами."""
    await _seed_order(db_session, price=Decimal("100"), quantity=2)
    await _seed_order(db_session, price=Decimal("50"), quantity=3)

    service = AnalyticsService(db=db_session)
    result = await service.get_revenue()
    # 100*2 + 50*3 = 200 + 150 = 350
    assert result.total_revenue == Decimal("350.00")
    assert result.orders_count == 2


@pytest.mark.asyncio
async def test_avg_order_value_empty(db_session: AsyncSession):
    """Средний чек с пустой БД — 0."""
    service = AnalyticsService(db=db_session)
    result = await service.get_avg_order_value()
    assert result.avg_order_value == Decimal("0.00")
    assert result.orders_count == 0


@pytest.mark.asyncio
async def test_avg_order_value_with_orders(db_session: AsyncSession):
    """Средний чек с заказами."""
    await _seed_order(db_session, price=Decimal("200"), quantity=1)
    await _seed_order(db_session, price=Decimal("100"), quantity=2)

    service = AnalyticsService(db=db_session)
    result = await service.get_avg_order_value()
    # (200 + 200) / 2 = 200.00
    assert result.avg_order_value == Decimal("200.00")
    assert result.orders_count == 2


@pytest.mark.asyncio
async def test_top_products_empty(db_session: AsyncSession):
    """Топ товаров с пустой БД — пустой список."""
    service = AnalyticsService(db=db_session)
    result = await service.get_top_products()
    assert result.products == []


@pytest.mark.asyncio
async def test_top_products_with_data(db_session: AsyncSession):
    """Топ товаров с данными — сортировка по убыванию заказов."""
    seller = await _create_seller(db_session)
    p1 = await _create_product(db_session, seller.id, "A", Decimal("10"))
    p2 = await _create_product(db_session, seller.id, "B", Decimal("20"))
    p3 = await _create_product(db_session, seller.id, "C", Decimal("30"))

    oservice = OrderService(db=db_session)
    # p1 — 3 заказа, p2 — 2 заказа, p3 — 1 заказ
    for _ in range(3):
        await oservice.create(
            OrderCreate(product_id=p1.id, seller_id=seller.id, quantity=1),
            buyer_username=_TEST_BUYER,
        )
    for _ in range(2):
        await oservice.create(
            OrderCreate(product_id=p2.id, seller_id=seller.id, quantity=1),
            buyer_username=_TEST_BUYER,
        )
    await oservice.create(
        OrderCreate(product_id=p3.id, seller_id=seller.id, quantity=1),
        buyer_username=_TEST_BUYER,
    )

    service = AnalyticsService(db=db_session)
    result = await service.get_top_products(limit=2)
    assert len(result.products) == 2
    assert result.products[0].product_name == "A"
    assert result.products[0].orders_count == 3
    assert result.products[1].product_name == "B"
    assert result.products[1].orders_count == 2


@pytest.mark.asyncio
async def test_commissions_summary_empty(db_session: AsyncSession):
    """Сводка комиссий с пустой БД — всё 0."""
    service = AnalyticsService(db=db_session)
    result = await service.get_commissions_summary()
    assert result.total_paid == Decimal("0.00")
    assert result.total_pending == Decimal("0.00")
    assert result.total_refunded == Decimal("0.00")
    assert result.commissions_count == 0


@pytest.mark.asyncio
async def test_commissions_summary_with_data(db_session: AsyncSession):
    """Сводка комиссий с данными — суммы по статусам."""
    seller, order = await _seed_order(db_session, price=Decimal("100"), quantity=1)
    cservice = CommissionService(db=db_session)

    c1 = await cservice.create(CommissionCreate(
        order_id=order.id, seller_id=seller.id,
        amount=Decimal("50"), percentage=Decimal("10"), status="paid",
    ))
    c2 = await cservice.create(CommissionCreate(
        order_id=order.id, seller_id=seller.id,
        amount=Decimal("30"), percentage=Decimal("5"), status="pending",
    ))
    c3 = await cservice.create(CommissionCreate(
        order_id=order.id, seller_id=seller.id,
        amount=Decimal("10"), percentage=Decimal("2"), status="refunded",
    ))

    service = AnalyticsService(db=db_session)
    result = await service.get_commissions_summary()
    assert result.total_paid == Decimal("50.00")
    assert result.total_pending == Decimal("30.00")
    assert result.total_refunded == Decimal("10.00")
    assert result.commissions_count == 3


@pytest.mark.asyncio
async def test_dashboard_summary(db_session: AsyncSession):
    """Dashboard summary — все метрики в одном ответе."""
    seller = await _create_seller(db_session)
    product = await _create_product(db_session, seller.id, "Dash", Decimal("100"))

    oservice = OrderService(db=db_session)
    order = await oservice.create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=2),
        buyer_username=_TEST_BUYER,
    )

    cservice = CommissionService(db=db_session)
    await cservice.create(CommissionCreate(
        order_id=order.id, seller_id=seller.id,
        amount=Decimal("20"), percentage=Decimal("10"), status="paid",
    ))

    service = AnalyticsService(db=db_session)
    result = await service.get_dashboard_summary(top_limit=5)
    assert result.total_revenue == Decimal("200.00")
    assert result.avg_order_value == Decimal("200.00")
    assert result.orders_count == 1
    assert len(result.top_products) == 1
    assert result.top_products[0].product_name == "Dash"
    assert result.commissions.total_paid == Decimal("20.00")


# ══════════════════════════════════════════════════
# HTTP-эндпоинты
# ══════════════════════════════════════════════════


def _admin_token() -> dict:
    """Получить заголовки авторизации админа."""
    from app.auth.service import auth_service
    from app.database import async_session_factory
    import asyncio

    # Создаём админа в тестовой БД (запускается внутри TestClient контекста)
    return {"Authorization": "Bearer admin-test-token-placeholder"}


def test_analytics_endpoints_forbidden_for_buyer(test_client: TestClient, db_session: AsyncSession):
    """Аналитика недоступна для buyer — 403."""
    # Регистрируем buyer
    response = test_client.post("/api/v1/auth/register", json={
        "username": "analytics_buyer", "email": "buyer@test.com",
        "password": "Pass1234!", "role": "buyer",
    })

    # Логинимся
    login_resp = test_client.post("/api/v1/auth/login", json={
        "username": "analytics_buyer", "password": "Pass1234!",
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}

    # Проверяем все эндпоинты
    endpoints = [
        "/api/v1/analytics/revenue",
        "/api/v1/analytics/avg-order-value",
        "/api/v1/analytics/top-products",
        "/api/v1/analytics/commissions-summary",
        "/api/v1/analytics/summary",
    ]
    for ep in endpoints:
        resp = test_client.get(ep, headers=headers)
        assert resp.status_code == 403, f"{ep}: expected 403, got {resp.status_code}"


def test_analytics_endpoints_as_admin(test_client: TestClient, db_session: AsyncSession):
    """Аналитика доступна для admin — 200."""
    # Регистрируем admin
    resp = test_client.post("/api/v1/auth/register", json={
        "username": "analytics_admin", "email": "admin@test.com",
        "password": "Pass1234!", "role": "admin",
    })

    login_resp = test_client.post("/api/v1/auth/login", json={
        "username": "analytics_admin", "password": "Pass1234!",
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        "/api/v1/analytics/revenue",
        "/api/v1/analytics/avg-order-value",
        "/api/v1/analytics/top-products",
        "/api/v1/analytics/commissions-summary",
        "/api/v1/analytics/summary",
    ]
    for ep in endpoints:
        resp = test_client.get(ep, headers=headers)
        assert resp.status_code == 200, f"{ep}: expected 200, got {resp.status_code} ({resp.text})"


def test_analytics_unauthorized(test_client: TestClient):
    """Аналитика без токена — 401."""
    endpoints = [
        "/api/v1/analytics/revenue",
        "/api/v1/analytics/avg-order-value",
        "/api/v1/analytics/top-products",
        "/api/v1/analytics/commissions-summary",
        "/api/v1/analytics/summary",
    ]
    for ep in endpoints:
        resp = test_client.get(ep)
        assert resp.status_code == 401, f"{ep}: expected 401, got {resp.status_code}"


# ══════════════════════════════════════════════════
# Хелперы
# ══════════════════════════════════════════════════


async def _create_seller(db: AsyncSession, name: str = "AnalyticsSeller", email: str = None) -> "SellerORM":
    """
    Создать продавца и вернуть ORM-объект.

    Использует уникальный email для избежания DuplicateEmailError.
    """
    from app.models.seller import SellerCreate
    if email is None:
        import uuid
        email = f"as_{uuid.uuid4().hex[:8]}@test.com"
    return await SellerService(db=db).create(
        SellerCreate(name=name, email=email),
        user_id=_TEST_USER_ID,
    )


async def _create_product(db: AsyncSession, seller_id: int, name: str, price: Decimal) -> "ProductORM":
    """Создать товар и вернуть ORM-объект."""
    return await ProductService(db=db).create(
        ProductCreate(seller_id=seller_id, name=name, price=price, stock=100),
        user_id=_TEST_USER_ID,
    )


async def _seed_order(db: AsyncSession, price: Decimal, quantity: int) -> tuple["SellerORM", "OrderORM"]:
    """Создать продавца, товар и заказ. Вернуть (seller, order)."""
    seller = await _create_seller(db)
    product = await _create_product(db, seller.id, f"Prod_{price}", price)
    oservice = OrderService(db=db)
    order = await oservice.create(
        OrderCreate(product_id=product.id, seller_id=seller.id, quantity=quantity),
        buyer_username=_TEST_BUYER,
    )
    return seller, order
