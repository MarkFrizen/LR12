import pytest
from fastapi import Request
from fastapi.responses import JSONResponse
from unittest.mock import AsyncMock

from app.exceptions import MarketPlaceError, marketplace_exception_handler


@pytest.mark.asyncio
async def test_marketplace_exception_handler():
    """Проверяет, что marketplace_exception_handler возвращает корректный JSON-ответ."""
    # Создаем мок запроса
    mock_request = AsyncMock(spec=Request)
    mock_request.scope = {
        "type": "http",
        "method": "GET",
        "path": "/test",
    }
    
    # Создаем исключение
    exc = MarketPlaceError("Test error", 400)
    
    # Вызываем обработчик
    response = await marketplace_exception_handler(mock_request, exc)
    
    # Проверяем ответ
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    assert response.body == b'{"detail":"Test error"}'