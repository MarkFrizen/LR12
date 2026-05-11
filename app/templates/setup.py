"""
Настройка Jinja2-шаблонизатора для frontend-страниц.
Создаёт собственное окружение Jinja2 вместо Jinja2Templates
для избежания проблем с кэшированием LRUCache.
"""

from pathlib import Path

import jinja2
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import HTMLResponse
from starlette.templating import _TemplateResponse

BASE_DIR = Path(__file__).resolve().parent

# Создаём окружение Jinja2 напрямую, минуя Starlette Jinja2Templates
loader = jinja2.FileSystemLoader(searchpath=str(BASE_DIR))
env = jinja2.Environment(
    loader=loader,
    autoescape=jinja2.select_autoescape(),
    # Отключаем кэш LRUCache (он вызывает TypeError с weakref в нек. версиях)
    cache_size=0,
)


def setup_jinja(app: FastAPI) -> None:
    """Подключить маршруты для frontend-страниц."""

    def _render(name: str, request: Request, context: dict = None) -> _TemplateResponse:
        """Отрендерить шаблон."""
        tmpl = env.get_template(name)
        ctx = {"request": request}
        if context:
            ctx.update(context)
        return _TemplateResponse(tmpl, ctx)

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def index(request: Request):
        return _render("index.html", request)

    @app.get("/login", response_class=HTMLResponse, include_in_schema=False)
    async def login_page(request: Request):
        return _render("login.html", request)

    @app.get("/register", response_class=HTMLResponse, include_in_schema=False)
    async def register_page(request: Request):
        return _render("register.html", request)

    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard_page(request: Request):
        return _render("dashboard.html", request)

    @app.get("/products-page", response_class=HTMLResponse, include_in_schema=False)
    async def products_page(request: Request):
        return _render("products.html", request)

    @app.get("/orders-page", response_class=HTMLResponse, include_in_schema=False)
    async def orders_page(request: Request):
        return _render("orders.html", request)

    @app.get("/reviews-page", response_class=HTMLResponse, include_in_schema=False)
    async def reviews_page(request: Request):
        return _render("reviews.html", request)

    @app.get("/profile", response_class=HTMLResponse, include_in_schema=False)
    async def profile_page(request: Request):
        return _render("profile.html", request)

    @app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
    async def admin_page(request: Request):
        return _render("admin.html", request)
