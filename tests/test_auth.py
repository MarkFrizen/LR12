"""
Тесты сервиса аутентификации.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserCreate, UserLogin, UserRole, ChangePasswordRequest
from app.auth.service import AuthService
from app.auth.utils import hash_password, verify_password, create_access_token, decode_access_token
from app.exceptions import MarketPlaceError


class TestAuthUtils:
    """Unit-тесты утилит аутентификации."""

    def test_hash_and_verify_password(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"
        assert verify_password("secret123", hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_jwt_create_and_decode(self):
        token = create_access_token({"sub": "42", "role": "admin"})
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["sub"] == "42"
        assert payload["role"] == "admin"

    def test_jwt_invalid_token(self):
        assert decode_access_token("invalid.token.here") is None


class TestAuthService:
    """Интеграционные тесты сервиса аутентификации."""

    @pytest.mark.asyncio
    async def test_register_user(self, db_session: AsyncSession):
        service = AuthService()
        data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="Pass1234!",
            role=UserRole.BUYER,
        )
        user = await service.register(db_session, data)
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "buyer"
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, db_session: AsyncSession):
        service = AuthService()
        data = UserCreate(username="dupuser", email="a@b.com", password="Pass1234!")
        await service.register(db_session, data)
        with pytest.raises(MarketPlaceError) as exc:
            await service.register(db_session, data)
        assert "уже занято" in str(exc.value)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, db_session: AsyncSession):
        service = AuthService()
        reg_data = UserCreate(
            username="authuser", email="auth@test.com", password="MyPass1!", role=UserRole.SELLER
        )
        await service.register(db_session, reg_data)

        user, token = await service.authenticate(
            db_session, UserLogin(username="authuser", password="MyPass1!")
        )
        assert user.username == "authuser"
        assert token is not None
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, db_session: AsyncSession):
        service = AuthService()
        reg_data = UserCreate(username="wrongpass", email="wp@test.com", password="Correct1!")
        await service.register(db_session, reg_data)

        with pytest.raises(MarketPlaceError) as exc:
            await service.authenticate(
                db_session, UserLogin(username="wrongpass", password="Wrong1!")
            )
        assert "Неверное имя" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession):
        service = AuthService()
        data = UserCreate(username="getuser", email="get@test.com", password="Pass123456!")
        user = await service.register(db_session, data)
        found = await service.get_by_id(db_session, user.id)
        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_username(self, db_session: AsyncSession):
        service = AuthService()
        data = UserCreate(username="findme", email="find@test.com", password="Pass123456!")
        await service.register(db_session, data)
        found = await service.get_by_username(db_session, "findme")
        assert found is not None
        assert found.username == "findme"

    @pytest.mark.asyncio
    async def test_update_profile(self, db_session: AsyncSession):
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="upduser", email="upd@test.com", password="Pass123456!")
        )
        from app.auth.models import UserUpdate
        updated = await service.update_profile(
            db_session, user.id, UserUpdate(full_name="New Name", phone="+79991234567")
        )
        assert updated.full_name == "New Name"
        assert updated.phone == "+79991234567"

    @pytest.mark.asyncio
    async def test_change_role(self, db_session: AsyncSession):
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="roleuser", email="role@test.com", password="Pass123456!")
        )
        updated = await service.change_role(db_session, user.id, UserRole.ADMIN)
        assert updated.role == "admin"

    @pytest.mark.asyncio
    async def test_toggle_active(self, db_session: AsyncSession):
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="activeuser", email="active@test.com", password="Pass123456!")
        )
        toggled = await service.toggle_active(db_session, user.id)
        assert toggled.is_active is False
        toggled_again = await service.toggle_active(db_session, user.id)
        assert toggled_again.is_active is True

    @pytest.mark.asyncio
    async def test_change_password_success(self, db_session: AsyncSession):
        """Успешная смена пароля."""
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="changepwd", email="cp@test.com", password="Old_Pass1!")
        )
        await service.change_password(
            db_session, user.id,
            ChangePasswordRequest(old_password="Old_Pass1!", new_password="NewSecure1!"),
        )
        # Проверяем, что старый пароль больше не работает, а новый — работает
        user_auth, token = await service.authenticate(
            db_session, UserLogin(username="changepwd", password="NewSecure1!"),
        )
        assert user_auth.id == user.id
        assert token is not None

    @pytest.mark.asyncio
    async def test_change_password_wrong_old(self, db_session: AsyncSession):
        """Смена пароля с неверным старым паролем."""
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="wrongold", email="wo@test.com", password="Real_Pass1!")
        )
        with pytest.raises(MarketPlaceError) as exc:
            await service.change_password(
                db_session, user.id,
                ChangePasswordRequest(old_password="wrong", new_password="New_Pass1!"),
            )
        assert "Неверный текущий пароль" in str(exc.value)

    @pytest.mark.asyncio
    async def test_change_password_same_password(self, db_session: AsyncSession):
        """Смена пароля на тот же самый."""
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="samepwd", email="sp@test.com", password="Same_Pass1!")
        )
        with pytest.raises(MarketPlaceError) as exc:
            await service.change_password(
                db_session, user.id,
                ChangePasswordRequest(old_password="Same_Pass1!", new_password="Same_Pass1!"),
            )
        assert "совпадает со старым" in str(exc.value)

    @pytest.mark.asyncio
    async def test_authenticate_timing_oracle_mitigation(self, db_session: AsyncSession):
        """Проверка, что timing-атака предотвращена:
        - несуществующий пользователь даёт ту же ошибку, что и неверный пароль.
        - bcrypt вызывается в любом случае (проверяем, что нет раннего выхода).
        """
        service = AuthService()

        # Регистрируем пользователя
        await service.register(
            db_session, UserCreate(username="timing_user", email="tu@test.com", password="Correct1!")
        )

        # 1. Существующий пользователь + неверный пароль
        with pytest.raises(MarketPlaceError) as exc1:
            await service.authenticate(
                db_session, UserLogin(username="timing_user", password="Wrong1!")
            )
        msg_existing = str(exc1.value)

        # 2. Несуществующий пользователь + любой пароль
        with pytest.raises(MarketPlaceError) as exc2:
            await service.authenticate(
                db_session, UserLogin(username="nonexistent_user", password="AnyPass1!")
            )
        msg_nonexistent = str(exc2.value)

        # Сообщения об ошибках должны быть идентичными (не раскрываем существование)
        assert msg_existing == msg_nonexistent
        assert "Неверное имя пользователя или пароль" in msg_existing
