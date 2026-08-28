from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_session
from app.core.rate_limit import rate_limiter
from app.main import app
from app.models import OTP


@pytest.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as test_session:
        yield test_session
    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_session() -> AsyncGenerator[AsyncSession, None]:
        yield session

    app.dependency_overrides[get_session] = override_session
    rate_limiter.clear()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    rate_limiter.clear()


async def test_register_verify_login_refresh_and_me(client: AsyncClient, session: AsyncSession) -> None:
    credentials = {"email": "person@example.com", "password": "very-secure-password", "full_name": "Test Person"}
    response = await client.post("/auth/register", json=credentials)
    assert response.status_code == 201

    result = await session.exec(select(OTP).where(OTP.purpose == "register"))
    code = result.one().code
    response = await client.post("/auth/verify-otp", json={"email": credentials["email"], "code": code})
    assert response.status_code == 200
    tokens = response.json()

    response = await client.get("/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert response.json()["email"] == credentials["email"]

    response = await client.post("/auth/login", json={"email": credentials["email"], "password": credentials["password"]})
    assert response.status_code == 200
    response = await client.post("/auth/refresh", json={"refresh_token": response.json()["refresh_token"]})
    assert response.status_code == 200


async def test_password_reset_flow(client: AsyncClient, session: AsyncSession) -> None:
    email = "reset@example.com"
    await client.post("/auth/register", json={"email": email, "password": "original-password"})
    register_otp = (await session.exec(select(OTP).where(OTP.purpose == "register"))).one()
    await client.post("/auth/verify-otp", json={"email": email, "code": register_otp.code})

    response = await client.post("/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    reset_otp = (await session.exec(select(OTP).where(OTP.purpose == "reset_password"))).one()
    response = await client.post("/auth/reset-password", json={"email": email, "code": reset_otp.code,
                                                                 "new_password": "replacement-password"})
    assert response.status_code == 200
    response = await client.post("/auth/login", json={"email": email, "password": "replacement-password"})
    assert response.status_code == 200


async def test_login_rate_limit(client: AsyncClient) -> None:
    for _ in range(10):
        response = await client.post("/auth/login", json={"email": "missing@example.com", "password": "invalid"})
        assert response.status_code == 401
    response = await client.post("/auth/login", json={"email": "missing@example.com", "password": "invalid"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers

