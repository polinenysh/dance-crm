from httpx import AsyncClient

from app.modules.users.model import User


async def test_login(
    client: AsyncClient,
    owner: User,
) -> None:
    """Проверяет вход с корректными данными."""

    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": owner.email,
            "password": "owner-password",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]


async def test_login_with_wrong_password(
    client: AsyncClient,
    owner: User,
) -> None:
    """Проверяет отказ при неверном пароле."""

    response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": owner.email,
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль"


async def test_get_current_user(
    client: AsyncClient,
    owner: User,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет получение текущего пользователя."""

    response = await client.get(
        "/api/v1/auth/me",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == owner.id
    assert response.json()["email"] == owner.email
    assert "hashed_password" not in response.json()


async def test_get_current_user_without_token(
    client: AsyncClient,
) -> None:
    """Проверяет защиту эндпоинта текущего пользователя."""

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_refresh_tokens(
    client: AsyncClient,
    owner: User,
) -> None:
    """Проверяет обновление пары JWT-токенов."""

    login_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": owner.email,
            "password": "owner-password",
        },
    )

    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]
    assert response.json()["refresh_token"]


async def test_access_token_cannot_be_used_as_refresh(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет различие access- и refresh-токенов."""

    access_token = owner_headers["Authorization"].removeprefix("Bearer ")

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401


async def test_change_password(
    client: AsyncClient,
    owner: User,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет изменение пароля текущего пользователя."""

    response = await client.post(
        "/api/v1/auth/change-password",
        headers=owner_headers,
        json={
            "current_password": "owner-password",
            "new_password": "new-owner-password",
        },
    )

    assert response.status_code == 204

    old_password_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": owner.email,
            "password": "owner-password",
        },
    )

    new_password_response = await client.post(
        "/api/v1/auth/login",
        data={
            "username": owner.email,
            "password": "new-owner-password",
        },
    )

    assert old_password_response.status_code == 401
    assert new_password_response.status_code == 200
