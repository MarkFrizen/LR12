"""
Фикстуры (conftest) для тестов с SQLAlchemy + SQLite in-memory.

Использует aiosqlite для асинхронных тестов без PostgreSQL.
"""

import os

# Установка переменных окружения для тестовой среды
# (должна быть до любого импорта app-модулей)
os.environ.setdefault("MP_JWT_SECRET", "test-secret-key-not-for-production")

from collections.abc import AsyncGenerator
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base

# In-memory SQLite (aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Создать движок БД для тестовой сессии."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    return engine


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Создать чистую БД и сессию для каждого теста.

    После теста все таблицы удаляются.
    """
    # Создаём таблицы
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session
        await session.rollback()
        await session.close()

    # Удаляем таблицы после теста
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
