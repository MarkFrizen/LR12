"""
Базовый класс сервиса с общей логикой для всех сервисов.

Реализует принципы SOLID:
- SRP: единая ответственность — обёртка для CRUD
- DIP: зависит от AsyncSession (абстракции), не от конкретной БД
"""

from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """Базовый сервис с доступом к сессии БД."""

    def __init__(self, db: AsyncSession):
        self.db = db
