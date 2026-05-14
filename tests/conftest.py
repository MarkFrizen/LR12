"""
Фикстуры (conftest) для тестов с SQLAlchemy + SQLite in-memory.

Использует aiosqlite для асинхронных тестов без PostgreSQL.

Фикстуры:
- test_engine      — движок на :memory: (scope=session)
- db_session       — изолированная сессия на каждый тест
- override_get_db  — подмена зависимости FastAPI get_db
- mock_lifespan    — отключение lifespan для предотвращения подключения к реальной БД
- test_client      — FastAPI TestClient с переопределённой get_db и без реального lifespan
"""

import os

# Установка переменных окружения для тестовой среды
# (должна быть до любого импорта app-модулей)
os.environ.setdefault("MP_JWT_SECRET", "test-secret-key-not-for-production")

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.database import Base, get_db

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

    После теста все таблицы удаляются, поэтому каждый тест
    стартует с пустой БД.
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


@pytest_asyncio.fixture
async def override_get_db(db_session: AsyncSession) -> AsyncGenerator[None, None]:
    """
    Подменить зависимость get_db тестовой сессией.

    Используется вместе с test_client: пока контекст активен,
    все запросы через TestClient используют in-memory SQLite.
    """
    async def _override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    # Подмена в самом объекте приложения
    from app.main import app
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_lifespan(override_get_db: None) -> None:
    """
    Отключить lifespan FastAPI-приложения в тестах.

    Lifespan (app/main.py) использует реальный PostgreSQL engine.
    Заменяем его на no-op, чтобы TestClient не пытался подключиться
    к реальной БД. Таблицы создаются в db_session отдельно.
    """
    from app.main import app

    @asynccontextmanager
    async def noop_lifespan(_app: FastAPI):
        """Пустой lifespan — ничего не делает."""
        yield

    original = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan
    yield
    app.router.lifespan_context = original


@pytest.fixture
def test_client(mock_lifespan, override_get_db: None) -> TestClient:
    """
    FastAPI TestClient с изолированной тестовой БД.

    Все эндпоинты работают через in-memory SQLite;
    get_db подменена на db_session из override_get_db.
    Lifespan отключён (mock_lifespan) — реальная БД не требуется.
    """
    from app.main import app
    with TestClient(app) as client:
        yield client
