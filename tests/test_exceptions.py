import pytest
from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions import MarketPlaceError, marketplace_exception_handler


def test_marketplace_exception_handler():
    """Проверяет, что marketplace_exception_handler возвращает корректный JSON-ответ."""
    # Создаем мок запроса
    mock_request = Request(scope={
        "type": "http",
        "method": "GET",
        "path": "/test",
    })
    
    # Создаем исключение
    exc = MarketPlaceError("Test error", 400)
    
    # Вызываем обработчик
    response = marketplace_exception_handler(mock_request, exc)
    
    # Проверяем ответ
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    assert response.body == b'{"detail":"Test error"}'