"""
Тесты сервиса аутентификации.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserCreate, UserLogin, UserRole
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
            password="password123",
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
        data = UserCreate(username="dupuser", email="a@b.com", password="123456")
        await service.register(db_session, data)
        with pytest.raises(MarketPlaceError) as exc:
            await service.register(db_session, data)
        assert "уже занято" in str(exc.value)

    @pytest.mark.asyncio
    async def test_authenticate_success(self, db_session: AsyncSession):
        service = AuthService()
        reg_data = UserCreate(
            username="authuser", email="auth@test.com", password="mypass", role=UserRole.SELLER
        )
        await service.register(db_session, reg_data)

        user, token = await service.authenticate(
            db_session, UserLogin(username="authuser", password="mypass")
        )
        assert user.username == "authuser"
        assert token is not None
        assert len(token) > 0

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, db_session: AsyncSession):
        service = AuthService()
        reg_data = UserCreate(username="wrongpass", email="wp@test.com", password="correct")
        await service.register(db_session, reg_data)

        with pytest.raises(MarketPlaceError) as exc:
            await service.authenticate(
                db_session, UserLogin(username="wrongpass", password="wrong")
            )
        assert "Неверное имя" in str(exc.value)

    @pytest.mark.asyncio
    async def test_get_by_id(self, db_session: AsyncSession):
        service = AuthService()
        data = UserCreate(username="getuser", email="get@test.com", password="pass123456")
        user = await service.register(db_session, data)
        found = await service.get_by_id(db_session, user.id)
        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_get_by_username(self, db_session: AsyncSession):
        service = AuthService()
        data = UserCreate(username="findme", email="find@test.com", password="pass123456")
        await service.register(db_session, data)
        found = await service.get_by_username(db_session, "findme")
        assert found is not None
        assert found.username == "findme"

    @pytest.mark.asyncio
    async def test_update_profile(self, db_session: AsyncSession):
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="upduser", email="upd@test.com", password="pass123456")
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
            db_session, UserCreate(username="roleuser", email="role@test.com", password="pass123456")
        )
        updated = await service.change_role(db_session, user.id, UserRole.ADMIN)
        assert updated.role == "admin"

    @pytest.mark.asyncio
    async def test_toggle_active(self, db_session: AsyncSession):
        service = AuthService()
        user = await service.register(
            db_session, UserCreate(username="activeuser", email="active@test.com", password="pass123456")
        )
        toggled = await service.toggle_active(db_session, user.id)
        assert toggled.is_active is False
        toggled_again = await service.toggle_active(db_session, user.id)
        assert toggled_again.is_active is True
