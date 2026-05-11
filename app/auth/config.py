"""
Настройки JWT и секреты для аутентификации.

Расширяет базовый конфиг из app.config.
"""

from app.config import Settings


class AuthSettings(Settings):
    """Настройки аутентификации (JWT, хэширование)."""

    # Секретный ключ для подписи JWT
    jwt_secret_key: str = "super-secret-key-change-in-production-2026"
    # Алгоритм подписи JWT
    jwt_algorithm: str = "HS256"
    # Время жизни токена (минуты)
    jwt_expire_minutes: int = 1440  # 24 часа

    # Параметры bcrypt
    bcrypt_rounds: int = 12


auth_settings = AuthSettings()
