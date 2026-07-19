from typing import Any

from httpx import AsyncClient

from app.modules.dance_styles.model import DanceStyle


async def test_owner_can_create_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style_payload: dict[str, Any],
) -> None:
    """Проверяет создание направления руководителем."""

    response = await client.post(
        "/api/v1/dance-styles",
        headers=owner_headers,
        json=dance_style_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["name"] == dance_style_payload["name"]
    assert data["description"] == dance_style_payload["description"]
    assert data["is_active"] is True
    assert "created_at" in data
    assert "updated_at" in data


async def test_branch_admin_cannot_create_dance_style(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    dance_style_payload: dict[str, Any],
) -> None:
    """Проверяет запрет создания направления администратором."""

    response = await client.post(
        "/api/v1/dance-styles",
        headers=branch_admin_headers,
        json=dance_style_payload,
    )

    assert response.status_code == 403


async def test_unauthorized_user_cannot_create_dance_style(
    client: AsyncClient,
    dance_style_payload: dict[str, Any],
) -> None:
    """Проверяет защиту создания направления."""

    response = await client.post(
        "/api/v1/dance-styles",
        json=dance_style_payload,
    )

    assert response.status_code == 401


async def test_create_duplicate_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style: DanceStyle,
) -> None:
    """Проверяет уникальность названия направления."""

    response = await client.post(
        "/api/v1/dance-styles",
        headers=owner_headers,
        json={
            "name": dance_style.name,
            "description": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Направление с таким названием уже существует")


async def test_create_duplicate_dance_style_case_insensitive(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style: DanceStyle,
) -> None:
    """Проверяет регистронезависимую уникальность названия."""

    response = await client.post(
        "/api/v1/dance-styles",
        headers=owner_headers,
        json={
            "name": dance_style.name.lower(),
            "description": None,
        },
    )

    assert response.status_code == 409


async def test_get_dance_styles_without_authorization(
    client: AsyncClient,
) -> None:
    """Проверяет защиту списка направлений."""

    response = await client.get("/api/v1/dance-styles")

    assert response.status_code == 401


async def test_filter_active_dance_styles(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style: DanceStyle,
    inactive_dance_style: DanceStyle,
) -> None:
    """Проверяет получение только активных направлений."""

    response = await client.get(
        "/api/v1/dance-styles",
        headers=owner_headers,
        params={"active_only": True},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == dance_style.id


async def test_get_dance_style_by_id(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style: DanceStyle,
) -> None:
    """Проверяет получение направления по идентификатору."""

    response = await client.get(
        f"/api/v1/dance-styles/{dance_style.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == dance_style.id
    assert data["name"] == dance_style.name
    assert data["description"] == dance_style.description


async def test_get_nonexistent_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрос отсутствующего направления."""

    response = await client.get(
        "/api/v1/dance-styles/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Направление не найдено"


async def test_owner_can_update_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style: DanceStyle,
) -> None:
    """Проверяет обновление направления руководителем."""

    response = await client.patch(
        f"/api/v1/dance-styles/{dance_style.id}",
        headers=owner_headers,
        json={
            "name": "Dancehall Kids",
            "description": "Обновлённое описание",
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Dancehall Kids"
    assert data["description"] == "Обновлённое описание"
    assert data["is_active"] is False


async def test_update_dance_style_with_duplicate_name(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style: DanceStyle,
    second_dance_style: DanceStyle,
) -> None:
    """Проверяет запрет установки занятого названия."""

    response = await client.patch(
        f"/api/v1/dance-styles/{dance_style.id}",
        headers=owner_headers,
        json={"name": second_dance_style.name},
    )

    assert response.status_code == 409


async def test_branch_admin_cannot_update_dance_style(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    dance_style: DanceStyle,
) -> None:
    """Проверяет запрет обновления администратором."""

    response = await client.patch(
        f"/api/v1/dance-styles/{dance_style.id}",
        headers=branch_admin_headers,
        json={"name": "Новое название"},
    )

    assert response.status_code == 403
