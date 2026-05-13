import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import Base, engine, get_db


def test_base_has_metadata():
    """Проверяет, что Base имеет атрибут metadata."""
    assert hasattr(Base, "metadata")


def test_engine_creation():
    """Проверяет, что engine был создан и имеет правильные параметры."""
    assert engine is not None
    assert engine.dialect.name == "postgresql"


def test_get_db_dependency():
    """Проверяет, что get_db возвращает асинхронный генератор сессии."""
    db_gen = get_db()
    
    # Проверяем, что get_db возвращает генератор
    assert hasattr(db_gen, "__anext__")
    assert hasattr(db_gen, "__aiter__")
    
    # Проверяем, что при вызове генератора возвращается сессия
    session = next(db_gen.__aiter__())
    assert isinstance(session, AsyncSession)
    
    # Проверяем, что сессия закрывается после использования
    with pytest.raises(StopAsyncIteration):
        next(db_gen.__aiter__())