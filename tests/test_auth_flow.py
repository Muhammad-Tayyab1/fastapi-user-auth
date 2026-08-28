from httpx import AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import OTP

API = "/api/v1"


async def test_register_verify_login_refresh_and_me(client: AsyncClient, session: AsyncSession) -> None:
    credentials = {"email": "person@example.com", "password": "very-secure-password", "full_name": "Test Person"}
    response = await client.post(f"{API}/auth/register", json=credentials)
    assert response.status_code == 201

    result = await session.exec(select(OTP).where(OTP.purpose == "register"))
    code = result.one().code
    response = await client.post(f"{API}/auth/verify-otp", json={"email": credentials["email"], "code": code})
    assert response.status_code == 200
    tokens = response.json()

    response = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert response.status_code == 200
    assert response.json()["email"] == credentials["email"]

    response = await client.post(f"{API}/auth/login", json={"email": credentials["email"], "password": credentials["password"]})
    assert response.status_code == 200
    response = await client.post(f"{API}/auth/refresh", json={"refresh_token": response.json()["refresh_token"]})
    assert response.status_code == 200


async def test_password_reset_flow(client: AsyncClient, session: AsyncSession) -> None:
    email = "reset@example.com"
    await client.post(f"{API}/auth/register", json={"email": email, "password": "original-password"})
    register_otp = (await session.exec(select(OTP).where(OTP.purpose == "register"))).one()
    await client.post(f"{API}/auth/verify-otp", json={"email": email, "code": register_otp.code})

    response = await client.post(f"{API}/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    reset_otp = (await session.exec(select(OTP).where(OTP.purpose == "reset_password"))).one()
    response = await client.post(f"{API}/auth/reset-password", json={"email": email, "code": reset_otp.code,
                                                                 "new_password": "replacement-password"})
    assert response.status_code == 200
    response = await client.post(f"{API}/auth/login", json={"email": email, "password": "replacement-password"})
    assert response.status_code == 200


async def test_login_rate_limit(client: AsyncClient) -> None:
    for _ in range(10):
        response = await client.post(f"{API}/auth/login", json={"email": "missing@example.com", "password": "invalid"})
        assert response.status_code == 401
    response = await client.post(f"{API}/auth/login", json={"email": "missing@example.com", "password": "invalid"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


async def authenticated_headers(client: AsyncClient, session: AsyncSession, email: str) -> dict[str, str]:
    await client.post(f"{API}/auth/register", json={"email": email, "password": "very-secure-password"})
    otp = (await session.exec(select(OTP).where(OTP.purpose == "register").order_by(OTP.created_at.desc()))).first()
    assert otp is not None
    response = await client.post(f"{API}/auth/verify-otp", json={"email": email, "code": otp.code})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def test_user_owned_note_crud(client: AsyncClient, session: AsyncSession) -> None:
    headers = await authenticated_headers(client, session, "notes@example.com")

    response = await client.post(f"{API}/notes/", json={"title": "First note", "content": "Initial"}, headers=headers)
    assert response.status_code == 201
    note_id = response.json()["id"]

    response = await client.get(f"{API}/notes/", headers=headers)
    assert response.status_code == 200
    assert [note["id"] for note in response.json()] == [note_id]

    response = await client.patch(f"{API}/notes/{note_id}", json={"title": "Updated note"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "Updated note"

    response = await client.get(f"{API}/notes/{note_id}", headers=headers)
    assert response.status_code == 200

    other_headers = await authenticated_headers(client, session, "other-notes@example.com")
    assert (await client.get(f"{API}/notes/{note_id}", headers=other_headers)).status_code == 404

    response = await client.delete(f"{API}/notes/{note_id}", headers=headers)
    assert response.status_code == 204
    assert (await client.get(f"{API}/notes/{note_id}", headers=headers)).status_code == 404
