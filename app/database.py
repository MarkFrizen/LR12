"""
Настройка асинхронного подключения к PostgreSQL через SQLAlchemy.

Создаёт движок, фабрику сессий и предоставляет зависимость
для FastAPI (get_db).
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Базовый класс для всех ORM-моделей
class Base(DeclarativeBase):
    """Базовый класс SQLAlchemy с декларативным стилем."""
    pass


# Асинхронный движок SQLAlchemy
engine = create_async_engine(
    settings.database_url,
    echo=False,                         # Логировать SQL-запросы (False — отключено)
    pool_size=5,                        # Размер пула соединений
    max_overflow=10,                    # Дополнительные соединения при пике
    pool_pre_ping=True,                 # Проверка соединения перед выдачей
)


# Фабрика асинхронных сессий
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,            # Не устаревать объекты после commit
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость FastAPI, предоставляющая сессию БД.

    Сессия автоматически закрывается после завершения запроса.

    Yields:
        AsyncSession — сессия SQLAlchemy для работы с БД.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
