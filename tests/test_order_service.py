"""
Каркас тестов для OrderService.

Альтернатива существующему test_orders.py.
Использует переиспользуемые фикстуры (test_seller, test_product, test_order)
для сокращения бойлерплейта в каждом тесте.

Покрытие:
- Создание заказа (успех, ошибки: stock, seller, product)
- Расчёт total_price = price * quantity
- Списание остатка со склада
- Защита buyer_name (CWE-602)
- Получение по ID и списка с фильтрацией
- Обновление статуса
- Удаление
- API-эндпоинты через TestClient
"""

import pytest
import pytest_asyncio
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserCreate, UserRole
from app.auth.service import auth_service
from app.auth.utils import create_access_token
from app.exceptions import (
    InsufficientStockError,
    OrderNotFoundError,
    ProductNotFoundError,
    SellerNotFoundError,
)
from app.models.order import OrderCreate, OrderORM, OrderStatus, OrderUpdate
from app.models.product import ProductCreate, ProductORM
from app.models.seller import SellerCreate, SellerORM
from app.services.order_service import OrderService
from app.services.product_service import ProductService
from app.services.seller_service import SellerService


# ════════════════════════════════════════════════════════
# КОНСТАНТЫ
# ════════════════════════════════════════════════════════

_BUYER_USERNAME = "test_buyer_ord"
_SELLER_USERNAME = "test_seller_ord"
_PASSWORD = "testpass123"
_DEFAULT_USER_ID = 1
_MOD_ROLE = "admin"
_PROD_PRICE = Decimal("100.00")
_PROD_STOCK = 10


# ════════════════════════════════════════════════════════
# ФИКСТУРЫ
# ════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def order_service(db_session: AsyncSession) -> OrderService:
    """OrderService с привязанной тестовой сессией."""
    return OrderService(db=db_session)


@pytest_asyncio.fixture
async def test_seller(db_session: AsyncSession) -> SellerORM:
    """Создать и вернуть продавца для тестов заказов."""
    return await SellerService(db=db_session).create(
        SellerCreate(name="OrdTestSeller", email="ordseller@test.com"),
        user_id=_DEFAULT_USER_ID,
    )


@pytest_asyncio.fixture
async def test_product(
    db_session: AsyncSession, test_seller: SellerORM
) -> ProductORM:
    """
    Товар с фиксированной ценой 100.00 и остатком 10.
    """
    return await ProductService(db=db_session).create(
        ProductCreate(
            seller_id=test_seller.id,
            name="DemoItem",
            price=_PROD_PRICE,
            stock=_PROD_STOCK,
            category="Тест",
        ),
        user_id=_DEFAULT_USER_ID,
    )


@pytest_asyncio.fixture
async def test_order(
    db_session: AsyncSession,
    order_service: OrderService,
    test_product: ProductORM,
    test_seller: SellerORM,
) -> OrderORM:
    """Заранее созданный заказ (qty=2, total=200.00, status=pending)."""
    return await order_service.create(
        OrderCreate(
            product_id=test_product.id,
            seller_id=test_seller.id,
            quantity=2,
        ),
        buyer_username=_BUYER_USERNAME,
    )


@pytest_asyncio.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, str]:
    """Зарегистрировать покупателя и вернуть Bearer-заголовки."""
    user = await auth_service.register(
        db_session,
        UserCreate(
            username=_BUYER_USERNAME,
            email="buyer_ord@test.com",
            password=_PASSWORD,
            role=UserRole.BUYER,
        ),
    )
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"Authorization": f"Bearer {token}"}


# ════════════════════════════════════════════════════════
# ТЕСТЫ: OrderService.create()
# ════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_order_success(
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """
    Создание заказа: проверка ID, суммы, статуса по умолчанию,
    имени покупателя.
    """
    order = await order_service.create(
        OrderCreate(
            product_id=test_product.id,
            seller_id=test_seller.id,
            quantity=3,
        ),
        buyer_username=_BUYER_USERNAME,
    )
    assert order.id is not None
    assert order.total_price == Decimal("300.00")  # 100 * 3
    assert order.status == OrderStatus.PENDING.value
    assert order.buyer_name == _BUYER_USERNAME


@pytest.mark.asyncio
async def test_create_order_calculates_total_price(
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """total_price = price * quantity — проверка для малых quantity."""
    for qty in (1, 2, 3):
        order = await order_service.create(
            OrderCreate(
                product_id=test_product.id,
                seller_id=test_seller.id,
                quantity=qty,
            ),
            buyer_username="qty_test",
        )
        assert order.total_price == _PROD_PRICE * Decimal(str(qty))


@pytest.mark.asyncio
async def test_create_order_insufficient_stock(
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """Заказ на 11 единиц при stock=10 → InsufficientStockError."""
    with pytest.raises(InsufficientStockError):
        await order_service.create(
            OrderCreate(
                product_id=test_product.id,
                seller_id=test_seller.id,
                quantity=_PROD_STOCK + 1,
            ),
            buyer_username="stock_test",
        )


@pytest.mark.asyncio
async def test_create_order_seller_not_found(
    order_service: OrderService,
    test_product: ProductORM,
):
    """seller_id=9999 → SellerNotFoundError."""
    with pytest.raises(SellerNotFoundError):
        await order_service.create(
            OrderCreate(
                product_id=test_product.id,
                seller_id=9999,
                quantity=1,
            ),
            buyer_username="no_seller",
        )


@pytest.mark.asyncio
async def test_create_order_product_not_found(
    order_service: OrderService,
    test_seller: SellerORM,
):
    """product_id=9999 → ProductNotFoundError."""
    with pytest.raises(ProductNotFoundError):
        await order_service.create(
            OrderCreate(
                product_id=9999,
                seller_id=test_seller.id,
                quantity=1,
            ),
            buyer_username="no_product",
        )


@pytest.mark.asyncio
async def test_create_order_decrements_stock(
    db_session: AsyncSession,
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """После создания заказа остаток товара уменьшается на quantity."""
    await order_service.create(
        OrderCreate(
            product_id=test_product.id,
            seller_id=test_seller.id,
            quantity=4,
        ),
        buyer_username="stock_dec",
    )
    updated = await ProductService(db=db_session).get_by_id(test_product.id)
    assert updated.stock == _PROD_STOCK - 4


@pytest.mark.asyncio
async def test_create_order_buyer_name_from_jwt_not_body(
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """
    buyer_name берётся из аргумента вызова, а не из тела запроса
    (защита от подмены CWE-602).
    """
    order = await order_service.create(
        OrderCreate(
            product_id=test_product.id,
            seller_id=test_seller.id,
            quantity=1,
            buyer_name="hacker",  # ← это поле игнорируется сервисом
        ),
        buyer_username="real_user_from_jwt",
    )
    assert order.buyer_name == "real_user_from_jwt"
    assert order.buyer_name != "hacker"


# ════════════════════════════════════════════════════════
# ТЕСТЫ: OrderService.get_by_id()
# ════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_order_by_id_success(
    order_service: OrderService,
    test_order: OrderORM,
):
    """Получение существующего заказа."""
    found = await order_service.get_by_id(test_order.id)
    assert found.id == test_order.id
    assert found.total_price == test_order.total_price


@pytest.mark.asyncio
async def test_get_order_by_id_not_found(
    order_service: OrderService,
):
    """Несуществующий ID → OrderNotFoundError."""
    with pytest.raises(OrderNotFoundError):
        await order_service.get_by_id(9999)


# ════════════════════════════════════════════════════════
# ТЕСТЫ: OrderService.get_all()
# ════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_orders_empty(order_service: OrderService):
    """Без заказов — пустой список."""
    assert await order_service.get_all() == []


@pytest.mark.asyncio
async def test_list_orders_with_data(
    order_service: OrderService,
    test_order: OrderORM,
):
    """Один созданный заказ присутствует в списке."""
    orders = await order_service.get_all()
    assert len(orders) == 1
    assert orders[0].id == test_order.id


@pytest.mark.asyncio
async def test_list_orders_filter_by_seller(
    order_service: OrderService,
    test_order: OrderORM,
):
    """Фильтрация по seller_id."""
    by_existing = await order_service.get_all(seller_id=test_order.seller_id)
    assert len(by_existing) >= 1

    by_missing = await order_service.get_all(seller_id=9999)
    assert by_missing == []


@pytest.mark.asyncio
async def test_list_orders_filter_by_status(
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """Фильтрация по статусу."""
    await order_service.create(
        OrderCreate(product_id=test_product.id, seller_id=test_seller.id, quantity=1),
        buyer_username="a",
    )
    await order_service.create(
        OrderCreate(product_id=test_product.id, seller_id=test_seller.id, quantity=1),
        buyer_username="b",
    )
    pending = await order_service.get_all(status="pending")
    assert len(pending) == 2


# ════════════════════════════════════════════════════════
# ТЕСТЫ: OrderService.update_status()
# ════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_update_order_status(
    order_service: OrderService,
    test_order: OrderORM,
):
    """Обновление статуса модератором: pending → shipped."""
    updated = await order_service.update_status(
        test_order.id,
        OrderUpdate(status=OrderStatus.SHIPPED),
        user_id=_DEFAULT_USER_ID,
        user_role=_MOD_ROLE,
    )
    assert updated.status == OrderStatus.SHIPPED.value


@pytest.mark.asyncio
async def test_update_order_status_by_owner_seller(
    order_service: OrderService,
    test_order: OrderORM,
):
    """Продавец-владелец может обновить статус своего заказа."""
    updated = await order_service.update_status(
        test_order.id,
        OrderUpdate(status=OrderStatus.CONFIRMED),
        user_id=test_order.seller_id,  # владелец
        user_role="seller",            # не модератор, но владелец
    )
    assert updated.status == OrderStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_update_order_status_forbidden_non_owner(
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """
    Чужой заказ (seller_id != user_id) + роль без прав
    → HTTPException(403).
    """
    # order_service.create возвращает order с seller_id = test_seller.id
    # user_id=999 не равен seller_id, role="buyer" не модераторская
    order = await order_service.create(
        OrderCreate(product_id=test_product.id, seller_id=test_seller.id, quantity=1),
        buyer_username="victim",
    )
    with pytest.raises(Exception) as exc_info:
        await order_service.update_status(
            order.id,
            OrderUpdate(status=OrderStatus.SHIPPED),
            user_id=999,         # не владелец
            user_role="buyer",   # не модератор
        )
    # Проверяем, что это именно HTTPException с кодом 403
    from fastapi import HTTPException
    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 403


# ════════════════════════════════════════════════════════
# ТЕСТЫ: OrderService.create() — множественные заказы
# ════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_multiple_orders_same_product(
    db_session: AsyncSession,
    order_service: OrderService,
    test_seller: SellerORM,
    test_product: ProductORM,
):
    """
    Последовательное резервирование одного товара:
    каждый заказ уменьшает stock, при исчерпании — InsufficientStockError.
    """
    # Первый заказ: 4 ед. → stock: 10 → 6
    o1 = await order_service.create(
        OrderCreate(product_id=test_product.id, seller_id=test_seller.id, quantity=4),
        buyer_username="u1",
    )
    assert o1.total_price == Decimal("400.00")

    # Второй заказ: 3 ед. → stock: 6 → 3
    o2 = await order_service.create(
        OrderCreate(product_id=test_product.id, seller_id=test_seller.id, quantity=3),
        buyer_username="u2",
    )
    assert o2.total_price == Decimal("300.00")

    # Третий заказ: 3 ед. → stock: 3 → 0 — успешно
    o3 = await order_service.create(
        OrderCreate(product_id=test_product.id, seller_id=test_seller.id, quantity=3),
        buyer_username="u3",
    )
    assert o3.total_price == Decimal("300.00")

    # Проверяем остаток
    updated = await ProductService(db=db_session).get_by_id(test_product.id)
    assert updated.stock == 0  # 10 - 4 - 3 - 3 = 0

    # Четвёртый заказ: stock=0 → InsufficientStockError
    with pytest.raises(InsufficientStockError):
        await order_service.create(
            OrderCreate(product_id=test_product.id, seller_id=test_seller.id, quantity=1),
            buyer_username="u4",
        )


# ════════════════════════════════════════════════════════
# ТЕСТЫ: OrderService.delete()
# ════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_delete_order(
    order_service: OrderService,
    test_order: OrderORM,
):
    """После удаления заказ перестаёт существовать."""
    await order_service.delete(test_order.id)
    with pytest.raises(OrderNotFoundError):
        await order_service.get_by_id(test_order.id)


# ════════════════════════════════════════════════════════
# ТЕСТЫ: API (TestClient)
# ════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_api_create_order(
    test_client,
    auth_headers: dict[str, str],
    test_seller: SellerORM,
    test_product: ProductORM,
):
    '''POST /api/v1/orders — 201 + тело ответа.'''
    response = test_client.post(
        "/api/v1/orders",
        json={
            "product_id": test_product.id,
            "seller_id": test_seller.id,
            "quantity": 2,
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total_price"] == "200.00"


@pytest.mark.asyncio
async def test_api_create_order_unauthorized(test_client):
    '''POST /api/v1/orders без токена → 401.'''
    response = test_client.post(
        "/api/v1/orders",
        json={"product_id": 1, "seller_id": 1, "quantity": 1},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_api_list_orders(
    test_client,
    auth_headers: dict[str, str],
):
    '''GET /api/v1/orders — 200 + список.'''
    response = test_client.get("/api/v1/orders", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
