from typing import Any

from httpx import AsyncClient


async def test_create_branch(
    client: AsyncClient,
    branch_payload: dict[str, Any],
    owner_headers: dict[str, str],
) -> None:
    """Проверяет создание филиала владельцем."""

    response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json=branch_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["name"] == branch_payload["name"]
    assert data["address"] == branch_payload["address"]
    assert data["phone"] == branch_payload["phone"]
    assert data["is_active"] is True
    assert "created_at" in data
    assert "updated_at" in data


async def test_get_branches(
    client: AsyncClient,
    branch_payload: dict[str, Any],
    owner_headers: dict[str, str],
) -> None:
    """Проверяет получение списка филиалов авторизованным пользователем."""

    create_response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json=branch_payload,
    )
    assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/branches",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == branch_payload["name"]


async def test_get_branch_by_id(
    client: AsyncClient,
    branch_payload: dict[str, Any],
    owner_headers: dict[str, str],
) -> None:
    """Проверяет получение филиала по идентификатору."""

    create_response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json=branch_payload,
    )
    assert create_response.status_code == 201

    branch_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/branches/{branch_id}",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == branch_id


async def test_get_nonexistent_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет ошибку при запросе отсутствующего филиала."""

    response = await client.get(
        "/api/v1/branches/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Филиал не найден"


async def test_create_duplicate_branch(
    client: AsyncClient,
    branch_payload: dict[str, Any],
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрет одинаковых названий филиалов."""

    first_response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json=branch_payload,
    )

    second_response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json=branch_payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


async def test_update_branch(
    client: AsyncClient,
    branch_payload: dict[str, Any],
    owner_headers: dict[str, str],
) -> None:
    """Проверяет частичное обновление филиала владельцем."""

    create_response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json=branch_payload,
    )
    assert create_response.status_code == 201

    branch_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/branches/{branch_id}",
        headers=owner_headers,
        json={
            "name": "Обновлённый филиал",
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Обновлённый филиал"
    assert response.json()["is_active"] is False


async def test_create_branch_with_too_long_phone(
    client: AsyncClient,
    branch_payload: dict[str, Any],
    owner_headers: dict[str, str],
) -> None:
    """Проверяет ограничение длины телефонного номера."""

    branch_payload["phone"] = "+799912345678"

    response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json=branch_payload,
    )

    assert response.status_code == 422


async def test_unauthorized_user_cannot_get_branches(
    client: AsyncClient,
) -> None:
    """Проверяет защиту списка филиалов."""

    response = await client.get("/api/v1/branches")

    assert response.status_code == 401
