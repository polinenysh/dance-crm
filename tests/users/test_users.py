from httpx import AsyncClient

from app.modules.branches.model import Branch


async def test_owner_can_create_branch_admin(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет создание администратора руководителем."""

    response = await client.post(
        "/api/v1/users",
        headers=owner_headers,
        json={
            "email": "admin@example.com",
            "password": "admin-password",
            "first_name": "Анна",
            "last_name": "Иванова",
            "phone": "+79991112233",
            "role": "branch_admin",
            "branch_id": branch.id,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "admin@example.com"
    assert data["role"] == "branch_admin"
    assert data["branch_id"] == branch.id
    assert "password" not in data
    assert "hashed_password" not in data


async def test_create_branch_admin_without_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет обязательность филиала для администратора."""

    response = await client.post(
        "/api/v1/users",
        headers=owner_headers,
        json={
            "email": "admin@example.com",
            "password": "admin-password",
            "first_name": "Анна",
            "last_name": "Иванова",
            "phone": "+79991112233",
            "role": "branch_admin",
            "branch_id": None,
        },
    )

    assert response.status_code == 422


async def test_owner_cannot_have_branch(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрет привязки руководителя к филиалу."""

    response = await client.post(
        "/api/v1/users",
        headers=owner_headers,
        json={
            "email": "second-owner@example.com",
            "password": "owner-password",
            "first_name": "Вторая",
            "last_name": "Руководитель",
            "phone": None,
            "role": "owner",
            "branch_id": branch.id,
        },
    )

    assert response.status_code == 422


async def test_create_user_with_duplicate_email(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет уникальность email сотрудника."""

    payload = {
        "email": "admin2@example.com",
        "password": "admin-password",
        "first_name": "Мария",
        "last_name": "Петрова",
        "phone": None,
        "role": "branch_admin",
        "branch_id": branch.id,
    }

    first_response = await client.post(
        "/api/v1/users",
        headers=owner_headers,
        json=payload,
    )

    second_response = await client.post(
        "/api/v1/users",
        headers=owner_headers,
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


async def test_unauthorized_user_cannot_get_users(
    client: AsyncClient,
) -> None:
    """Проверяет защиту списка сотрудников."""

    response = await client.get("/api/v1/users")

    assert response.status_code == 401


async def test_owner_can_get_users(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет получение списка сотрудников руководителем."""

    response = await client.get(
        "/api/v1/users",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["role"] == "owner"


async def test_update_user(
    client: AsyncClient,
    branch: Branch,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет обновление данных сотрудника."""

    create_response = await client.post(
        "/api/v1/users",
        headers=owner_headers,
        json={
            "email": "admin3@example.com",
            "password": "admin-password",
            "first_name": "Мария",
            "last_name": "Петрова",
            "phone": None,
            "role": "branch_admin",
            "branch_id": branch.id,
        },
    )

    user_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{user_id}",
        headers=owner_headers,
        json={
            "first_name": "Екатерина",
            "is_active": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Екатерина"
    assert response.json()["is_active"] is False
