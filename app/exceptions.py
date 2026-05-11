"""
Кастомные исключения предметной области и глобальные обработчики ошибок FastAPI.

Позволяет единообразно возвращать ошибки клиенту в формате JSON.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class MarketPlaceError(Exception):
    """Базовое исключение для всех ошибок маркетплейса."""

    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class SellerNotFoundError(MarketPlaceError):
    """Продавец не найден в БД."""

    def __init__(self, seller_id: int):
        super().__init__(
            message=f"Продавец с id={seller_id} не найден.",
            status_code=404,
        )


class ProductNotFoundError(MarketPlaceError):
    """Товар не найден в БД."""

    def __init__(self, product_id: int):
        super().__init__(
            message=f"Товар с id={product_id} не найден.",
            status_code=404,
        )


class OrderNotFoundError(MarketPlaceError):
    """Заказ не найден в БД."""

    def __init__(self, order_id: int):
        super().__init__(
            message=f"Заказ с id={order_id} не найден.",
            status_code=404,
        )


class ReviewNotFoundError(MarketPlaceError):
    """Отзыв не найден в БД."""

    def __init__(self, review_id: int):
        super().__init__(
            message=f"Отзыв с id={review_id} не найден.",
            status_code=404,
        )


class CommissionNotFoundError(MarketPlaceError):
    """Комиссия не найдена в БД."""

    def __init__(self, commission_id: int):
        super().__init__(
            message=f"Комиссия с id={commission_id} не найдена.",
            status_code=404,
        )


class InsufficientStockError(MarketPlaceError):
    """Недостаточное количество товара на складе."""

    def __init__(self, product_id: int, requested: int, available: int):
        super().__init__(
            message=(
                f"Недостаточно товара id={product_id} на складе: "
                f"запрошено {requested}, доступно {available}."
            ),
            status_code=409,
        )


class DuplicateEmailError(MarketPlaceError):
    """Попытка создать продавца с уже существующим email."""

    def __init__(self, email: str):
        super().__init__(
            message=f"Продавец с email '{email}' уже существует.",
            status_code=409,
        )


# Регистрация глобального обработчика для FastAPI
async def marketplace_exception_handler(
    request: Request,
    exc: MarketPlaceError,
) -> JSONResponse:
    """
    Преобразует MarketPlaceError в JSON-ответ с соответствующим HTTP-статусом.

    Args:
        request: Объект HTTP-запроса FastAPI.
        exc: Экземпляр MarketPlaceError.

    Returns:
        JSONResponse с полями detail и status_code.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )
