"""
Точка входа FastAPI-приложения «Платформа маркетплейса».

Реализует:
- REST API (CRUD для 5 сущностей + аутентификация)
- Frontend (Jinja2 HTML-шаблоны + CSS + JS)
- JWT-аутентификацию и ролевую модель
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.exceptions import MarketPlaceError, marketplace_exception_handler
from app.logger import get_logger, setup_logging
from app.routers import (
    sellers,
    products,
    orders,
    reviews,
    commissions,
)
from app.auth.router import router as auth_router
from app.templates.setup import setup_jinja

# Настройка логирования при запуске
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Создание таблиц БД при старте, закрытие соединения при остановке."""
    logger.info("Запуск приложения Marketplace Platform")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Таблицы БД созданы/проверены")
    yield
    logger.info("Остановка приложения, закрытие соединения с БД")
    await engine.dispose()


app = FastAPI(
    title="Marketplace Platform API",
    description="REST API для платформы маркетплейса. Продавцы, товары, заказы, отзывы, комиссии.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Глобальный обработчик ошибок
app.add_exception_handler(MarketPlaceError, marketplace_exception_handler)

# Подключение статики
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Настройка Jinja2
setup_jinja(app)

# REST API роутеры
app.include_router(auth_router)
app.include_router(sellers.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(reviews.router)
app.include_router(commissions.router)


@app.get("/api/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}
