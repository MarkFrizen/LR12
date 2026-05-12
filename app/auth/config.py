"""
Настройки JWT и секреты для аутентификации.

Расширяет базовый конфиг из app.config.
Все секретные значения должны задаваться через .env или переменные окружения.
"""

from pydantic import Field

from app.config import Settings


class AuthSettings(Settings):
    """Настройки аутентификации (JWT, хэширование)."""

    # Секретный ключ для подписи JWT (обязателен!)
    jwt_secret_key: str = Field(default="", alias="MP_JWT_SECRET")
    # Алгоритм подписи JWT
    jwt_algorithm: str = "HS256"
    # Время жизни токена в минутах (по умолчанию 60 мин)
    jwt_expire_minutes: int = 60

    # Параметры bcrypt
    bcrypt_rounds: int = 12

    def validate_secrets(self) -> None:
        """
        Проверить, что все обязательные секреты заданы.

        Raises:
            RuntimeError: Если какой-либо секрет не задан.
        """
        if not self.jwt_secret_key:
            raise RuntimeError(
                "MP_JWT_SECRET не задан! "
                "Установите секретный ключ JWT в .env или переменной окружения.\n"
                "Пример: MP_JWT_SECRET=your-secure-random-string-here"
            )


auth_settings = AuthSettings()

# validate_secrets() вызывается при старте приложения (main.py),
# чтобы тесты без .env могли создать экземпляр без ошибки.
