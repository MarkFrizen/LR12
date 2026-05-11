"""
Утилиты для JWT и хэширования паролей.

Использует bcrypt напрямую (без passlib, т.к. bcrypt 5.x несовместим с passlib).
"""

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.auth.config import auth_settings


def hash_password(password: str) -> str:
    """
    Хэшировать пароль с помощью bcrypt.

    Args:
        password: Открытый пароль.

    Returns:
        Хэшированный пароль (строка).
    """
    salt = bcrypt.gensalt(rounds=auth_settings.bcrypt_rounds)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверить пароль против хэша.

    Args:
        plain_password: Открытый пароль.
        hashed_password: Хэш из БД.

    Returns:
        True если пароль совпадает.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict) -> str:
    """
    Создать JWT-токен доступа.

    Args:
        data: Словарь с payload (обязательно содержит 'sub').

    Returns:
        Закодированный JWT-токен.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=auth_settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        auth_settings.jwt_secret_key,
        algorithm=auth_settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict | None:
    """
    Декодировать и проверить JWT-токен.

    Args:
        token: Закодированный JWT-токен.

    Returns:
        Словарь с payload или None при ошибке.
    """
    try:
        payload = jwt.decode(
            token,
            auth_settings.jwt_secret_key,
            algorithms=[auth_settings.jwt_algorithm],
        )
        return payload
    except JWTError:
        return None
