import pytest
from app.config import Settings
from app.auth.config import AuthSettings


def test_settings_validate_db_password_no_password_non_postgres():
    """Проверяет, что validate_db_password() выбрасывает RuntimeError при отсутствии пароля и несистемном пользователе."""
    settings = Settings(db_user="user1", db_password="")
    with pytest.raises(RuntimeError) as exc:
        settings.validate_db_password()
    assert "MP_DB_PASSWORD не задан!" in str(exc.value)


def test_settings_validate_db_password_with_password():
    """Проверяет, что validate_db_password() не выбрасывает исключение при наличии пароля."""
    settings = Settings(db_user="user1", db_password="secret")
    # Не должно быть исключения
    settings.validate_db_password()

def test_settings_validate_db_password_no_password_postgres():
    """Проверяет, что validate_db_password() не выбрасывает исключение для пользователя postgres без пароля."""
    settings = Settings(db_user="postgres", db_password="")
    # Не должно быть исключения
    settings.validate_db_password()

def test_auth_settings_validate_secrets_no_jwt_secret(monkeypatch):
    """Проверяет, что validate_secrets() выбрасывает RuntimeError при отсутствии jwt_secret_key."""
    # conftest.py устанавливает MP_JWT_SECRET; убираем из окружения,
    # чтобы Pydantic не прочитал его и не переопределил пустую строку
    monkeypatch.delenv("MP_JWT_SECRET", raising=False)

    auth_settings = AuthSettings(jwt_secret_key="", _env_file=None)
    with pytest.raises(RuntimeError) as exc:
        auth_settings.validate_secrets()
    assert "MP_JWT_SECRET не задан!" in str(exc.value)


def test_auth_settings_validate_secrets_with_jwt_secret():
    """Проверяет, что validate_secrets() не выбрасывает исключение при наличии jwt_secret_key."""
    auth_settings = AuthSettings(jwt_secret_key="supersecret")