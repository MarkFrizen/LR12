import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, engine, get_db


def test_base_has_metadata():
    """Проверяет, что Base имеет атрибут metadata."""
    assert hasattr(Base, "metadata")


def test_engine_creation():
    """Проверяет, что engine был создан и имеет правильные параметры."""
    assert engine is not None
    assert engine.dialect.name == "postgresql"

@pytest.mark.asyncio
async def test_get_db_dependency():
    """Проверяет, что get_db возвращает асинхронный генератор сессии."""
    db_gen = get_db()
    
    # Проверяем, что get_db возвращает генератор
    assert hasattr(db_gen, "__anext__")
    assert hasattr(db_gen, "__aiter__")
    
    # Проверяем, что при вызове генератора возвращается сессия
    session = await db_gen.__anext__()
    assert isinstance(session, AsyncSession)
    
    # Проверяем, что сессия закрывается после использования
    with pytest.raises(StopAsyncIteration):
        await db_gen.__anext__()

@pytest.mark.asyncio
async def test_get_db_rollback_on_exception():
    """Проверяет, что при исключении в сессии вызывается rollback."""
    # Создаем мок сессии
    mock_session = AsyncMock(spec=AsyncSession)
    
    # Настраиваем генератор, чтобы он возвращал мок сессии
    async def mock_session_context():
        yield mock_session
    
    # Мокаем async_session_factory
    with patch("app.database.async_session_factory") as mock_factory:
        mock_factory.return_value.__aenter__.return_value = mock_session
        
        # Создаем генератор get_db
        db_gen = get_db()
        
        # Получаем сессию
        session = await db_gen.__anext__()
        assert session == mock_session
        
        # Имитируем исключение
        try:
            await db_gen.athrow(Exception("Test exception"))
        except Exception:
            pass
        
        # Проверяем, что был вызван rollback
        mock_session.rollback.assert_awaited_once()
        
        # Проверяем, что исключение проброшено дальше
        with pytest.raises(StopAsyncIteration):
            await db_gen.__anext__()