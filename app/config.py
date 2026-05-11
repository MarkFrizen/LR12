"""
Конфигурация подключения к базе данных PostgreSQL.

Использует pydantic-settings для валидации переменных окружения
и предоставления значений по умолчанию, соответствующих заданию.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки подключения к PostgreSQL."""

    # Имя сервера / хост базы данных
    db_host: str = "127.0.0.1"
    # Порт PostgreSQL по умолчанию
    db_port: int = 5432
    # Имя пользователя БД
    db_user: str = "mp_user"
    # Пароль пользователя БД
    db_password: str = "12345"
    # Имя базы данных
    db_name: str = "marketplace_platform"

    @property
    def database_url(self) -> str:
        """
        Сформировать синхронный DSN для SQLAlchemy.

        Returns:
            Строка подключения вида:
            postgresql+asyncpg://user:password@host:port/dbname
        """
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
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
