"""
Конфигурация подключения к базе данных PostgreSQL.

Использует pydantic-settings для валидации переменных окружения
и предоставления значений по умолчанию, соответствующих заданию.
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки подключения к PostgreSQL и общие параметры приложения."""

    # Имя сервера / хост базы данных
    db_host: str = "127.0.0.1"
    # Порт PostgreSQL по умолчанию
    db_port: int = 5432
    # Имя пользователя БД
    db_user: str = "mp_user"
    # Пароль пользователя БД (обязателен — не оставляйте пустым!)
    db_password: str = Field(default="", alias="MP_DB_PASSWORD")
    # Имя базы данных
    db_name: str = "marketplace_platform"

    # Разрешённые источники для CORS (через запятую)
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def database_url(self) -> str:
        """
        Сформировать асинхронный DSN для SQLAlchemy (asyncpg).

        Returns:
            Строка подключения вида:
            postgresql+asyncpg://user:password@host:port/dbname

        Note:
            Если пароль не задан (тесты с SQLite), возвращается URL
            с пустым паролем. Функция validate_db_password() вызовет
            ошибку при старте продакшен-приложения.
        """
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        """Список разрешённых CORS-источников."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def validate_db_password(self) -> None:
        """
        Проверить, что пароль БД задан перед подключением.

        Raises:
            RuntimeError: Если пароль не задан.
        """
        if not self.db_password:
            raise RuntimeError(
                "MP_DB_PASSWORD не задан! "
                "Установите пароль в .env или переменной окружения."
            )

    model_config = {
        # Разрешить чтение настроек из файла .env
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Префикс для переменных окружения, чтобы избежать конфликтов
        "env_prefix": "MP_",
    }


# Единственный экземпляр настроек для всего приложения
settings = Settings()
