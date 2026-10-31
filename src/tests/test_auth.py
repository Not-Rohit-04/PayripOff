import pytest
from sqlalchemy import select
from src.db import User
from src.security import verify_password, decode_access_token
from uuid import UUID


@pytest.mark.asyncio
async def test_user_registration(client):
    user_data = {
        "username": "Rohit",
        "email": "abc@gmail.com",
        "password": "securepass12345",
    }

    response = await client.post("/auth/register", json=user_data)
    response_data = response.json()

    assert response.status_code == 201
    assert response_data["username"] == "Rohit"
    assert response_data["email"] == "abc@gmail.com"
    assert "id" in response_data
    assert "created_at" in response_data
    assert "password" not in response_data
    assert "password_hash" not in response_data


@pytest.mark.asyncio
async def test_duplicate_email(client):

    await client.post(
        "/auth/register",
        json={
            "username": "Rohit",
            "email": "abc@gmail.com",
            "password": "secure1234pass",
        },
    )

    response = await client.post(
        "/auth/register",
        json={
            "username": "Bob",
            "email": "abc@gmail.com",
            "password": "secure4321pass",
        },
    )
    response_data = response.json()
    assert response.status_code == 409
    assert response_data["detail"] == "Username or email already register."


@pytest.mark.asyncio
async def test_duplicate_username(client):

    await client.post(
        "/auth/register",
        json={
            "username": "Rohit",
            "email": "abc@gmail.com",
            "password": "secure1234pass",
        },
    )

    response = await client.post(
        "/auth/register",
        json={
            "username": "Rohit",
            "email": "abcd@gmail.com",
            "password": "secure4321pass",
        },
    )
    response_data = response.json()
    assert response.status_code == 409
    assert response_data["detail"] == "Username or email already register."


@pytest.mark.asyncio
async def test_invalid_email(client):
    response = await client.post(
        "/auth/register",
        json={
            "username": "Rohit",
            "email": "not_an_email",
            "password": "secure123Pass",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_short_password(client):
    response = await client.post(
        "/auth/register",
        json={"username": "Rohit", "email": "abc@gmail.com", "password": "123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_empty_username(client):
    response = await client.post(
        "/auth/register",
        json={"username": "", "email": "abc@gmail.com", "password": "12345678"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_password_is_hashed(client, db_session):
    response = await client.post(
        "/auth/register",
        json={
            "username": "Rohit",
            "email": "abc@gmail.com",
            "password": "secure12345pass",
        },
    )
    assert response.status_code == 201

    response_data = response.json()
    result = await db_session.execute(
        select(User).where(User.id == UUID(response_data["id"]))
    )
    user = result.scalar_one_or_none()

    assert user is not None

    assert user.password_hash != "secure12345pass"

    assert (
        verify_password(password="secure12345pass", hash_password=user.password_hash)
        == True
    )


@pytest.mark.asyncio
async def test_successful_login(client):
    await client.post(
        "/auth/register",
        json={"username": "Rohit", "email": "abc@gmail.com", "password": "secure1234"},
    )

    response = await client.post(
        "/auth/login", json={"email": "abc@gmail.com", "password": "secure1234"}
    )

    assert response.status_code == 200

    response_data = response.json()

    assert "access_token" in response_data
    assert "token_type" in response_data
    assert response_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_incorrect_password(client):
    await client.post(
        "/auth/register",
        json={"username": "Rohit", "email": "abc@gmail.com", "password": "secure1234"},
    )

    response = await client.post(
        "/auth/login", json={"email": "abc@gmail.com", "password": "notpassword"}
    )

    assert response.status_code == 401

    response_data = response.json()

    assert response_data["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_non_registered_email(client):
    response = await client.post(
        "/auth/login", json={"email": "abc@gmail.com", "password": "secure12354"}
    )

    assert response.status_code == 401

    response_data = response.json()

    assert response_data["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_invalid_email(client):
    response = await client.post(
        "/auth/login", json={"email": "not an email", "password": "secure12354"}
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_JWT_validate(client, db_session):
    await client.post(
        "/auth/register",
        json={"username": "Rohit", "email": "abc@gmail.com", "password": "secure12354"},
    )
    response = await client.post(
        "/auth/login", json={"email": "abc@gmail.com", "password": "secure12354"}
    )
    assert response.status_code == 200
    response_data = response.json()

    result = await db_session.execute(select(User))

    user = result.scalar_one()

    payload = decode_access_token(token=response_data["access_token"])

    assert payload["sub"] == str(user.id)
