from uuid import uuid4  # <-- NEW IMPORT

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Generate a unique email for each test run to ensure no conflict
    unique_email = f"user_{uuid4()}@example.com"

    # register user
    payload = {"email": unique_email, "password": "StrongPass1!"}
    r = await client.post("/auth/register", json=payload)

    # Assert status code is 200 or 201 (success)
    assert r.status_code == 200 or r.status_code == 201
    data = r.json()
    assert data["email"] == unique_email

    # login via OAuth2 form (username/password)
    # httpx needs form data content type
    r2 = await client.post(
        "/auth/login", data={"username": unique_email, "password": "StrongPass1!"}
    )
    assert r2.status_code == 200
    token_data = r2.json()
    assert "access_token" in token_data


@pytest.mark.asyncio
async def test_register_invalid_password(client: AsyncClient):
    # missing special character
    payload = {"email": "badpass@example.com", "password": "NoSpecial1"}
    r = await client.post("/auth/register", json=payload)
    assert r.status_code == 422 or r.status_code == 400
