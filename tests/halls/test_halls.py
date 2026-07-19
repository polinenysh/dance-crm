from httpx import AsyncClient

from app.modules.branches.model import Branch


async def test_create_hall(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет создание зала."""

    response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json={
            "branch_id": branch.id,
            "name": "Большой зал",
            "capacity": 40,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["branch_id"] == branch.id
    assert data["name"] == "Большой зал"
    assert data["capacity"] == 40
    assert data["is_active"] is True


async def test_create_hall_for_nonexistent_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрет создания зала без существующего филиала."""

    response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json={
            "branch_id": 999999,
            "name": "Большой зал",
            "capacity": 40,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Филиал не найден"


async def test_create_hall_for_inactive_branch(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрет создания зала в неактивном филиале."""

    update_response = await client.patch(
        f"/api/v1/branches/{branch.id}",
        headers=owner_headers,
        json={"is_active": False},
    )
    assert update_response.status_code == 200

    response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json={
            "branch_id": branch.id,
            "name": "Большой зал",
            "capacity": 40,
        },
    )

    assert response.status_code == 409


async def test_create_duplicate_hall_in_branch(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет уникальность названия зала внутри филиала."""

    payload = {
        "branch_id": branch.id,
        "name": "Малый зал",
        "capacity": 15,
    }

    first_response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json=payload,
    )

    second_response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


async def test_same_hall_name_in_different_branches(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Разрешает одинаковые названия залов в разных филиалах."""

    second_branch_response = await client.post(
        "/api/v1/branches",
        headers=owner_headers,
        json={
            "name": "Второй филиал",
            "address": "ул. Вторая, 20",
            "phone": None,
        },
    )
    assert second_branch_response.status_code == 201

    second_branch_id = second_branch_response.json()["id"]

    first_response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json={
            "branch_id": branch.id,
            "name": "Большой зал",
            "capacity": 20,
        },
    )

    second_response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json={
            "branch_id": second_branch_id,
            "name": "Большой зал",
            "capacity": 30,
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


async def test_filter_halls_by_branch(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет фильтрацию залов по филиалу."""

    create_response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json={
            "branch_id": branch.id,
            "name": "Зал 1",
            "capacity": 20,
        },
    )
    assert create_response.status_code == 201

    response = await client.get(
        "/api/v1/halls",
        headers=owner_headers,
        params={"branch_id": branch.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["branch_id"] == branch.id


async def test_hall_capacity_must_be_positive(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрет нулевой вместимости зала."""

    response = await client.post(
        "/api/v1/halls",
        headers=owner_headers,
        json={
            "branch_id": branch.id,
            "name": "Неверный зал",
            "capacity": 0,
        },
    )

    assert response.status_code == 422


async def test_unauthorized_user_cannot_get_halls(
    client: AsyncClient,
) -> None:
    """Проверяет защиту списка залов."""

    response = await client.get("/api/v1/halls")

    assert response.status_code == 401
