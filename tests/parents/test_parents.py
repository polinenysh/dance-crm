from typing import Any

from httpx import AsyncClient

from app.modules.parents.model import Parent
from app.modules.students.model import Student


async def test_owner_can_create_parent(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent_payload: dict[str, Any],
) -> None:
    """Проверяет создание родителя руководителем."""

    response = await client.post(
        "/api/v1/parents",
        headers=owner_headers,
        json=parent_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["first_name"] == parent_payload["first_name"]
    assert data["last_name"] == parent_payload["last_name"]
    assert data["phone"] == parent_payload["phone"]
    assert data["comment"] is None
    assert "created_at" in data
    assert "updated_at" in data
    assert "email" not in data


async def test_branch_admin_can_create_parent(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    parent_payload: dict[str, Any],
) -> None:
    """Проверяет создание родителя администратором."""

    response = await client.post(
        "/api/v1/parents",
        headers=branch_admin_headers,
        json=parent_payload,
    )

    assert response.status_code == 201


async def test_unauthorized_user_cannot_create_parent(
    client: AsyncClient,
    parent_payload: dict[str, Any],
) -> None:
    """Проверяет защиту создания родителя."""

    response = await client.post(
        "/api/v1/parents",
        json=parent_payload,
    )

    assert response.status_code == 401


async def test_create_parent_with_duplicate_phone(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent: Parent,
) -> None:
    """Проверяет уникальность номера телефона родителя."""

    response = await client.post(
        "/api/v1/parents",
        headers=owner_headers,
        json={
            "first_name": "Другая",
            "last_name": "Родительница",
            "phone": parent.phone,
            "comment": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Родитель с таким телефоном уже существует"
    )


async def test_parent_phone_must_contain_twelve_characters(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent_payload: dict[str, Any],
) -> None:
    """Проверяет длину номера телефона родителя."""

    parent_payload["phone"] = "+7999000000"

    response = await client.post(
        "/api/v1/parents",
        headers=owner_headers,
        json=parent_payload,
    )

    assert response.status_code == 422


async def test_owner_can_get_parent(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent: Parent,
) -> None:
    """Проверяет получение родителя руководителем."""

    response = await client.get(
        f"/api/v1/parents/{parent.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == parent.id
    assert data["first_name"] == parent.first_name
    assert data["last_name"] == parent.last_name
    assert data["phone"] == parent.phone


async def test_get_nonexistent_parent(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет ошибку для отсутствующего родителя."""

    response = await client.get(
        "/api/v1/parents/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Родитель не найден"


async def test_owner_can_get_parents(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent: Parent,
    second_parent: Parent,
) -> None:
    """Проверяет получение списка родителей."""

    response = await client.get(
        "/api/v1/parents",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert {item["id"] for item in data} == {
        parent.id,
        second_parent.id,
    }


async def test_search_parents_by_last_name(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent: Parent,
    second_parent: Parent,
) -> None:
    """Проверяет поиск родителей по фамилии."""

    response = await client.get(
        "/api/v1/parents",
        headers=owner_headers,
        params={"search": second_parent.last_name},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == second_parent.id


async def test_search_parents_by_phone(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent: Parent,
) -> None:
    """Проверяет поиск родителей по телефону."""

    response = await client.get(
        "/api/v1/parents",
        headers=owner_headers,
        params={"search": parent.phone},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == parent.id


async def test_owner_can_update_parent(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent: Parent,
) -> None:
    """Проверяет обновление карточки родителя."""

    response = await client.patch(
        f"/api/v1/parents/{parent.id}",
        headers=owner_headers,
        json={
            "first_name": "Екатерина",
            "comment": "Обновлённый комментарий",
        },
    )

    assert response.status_code == 200
    assert response.json()["first_name"] == "Екатерина"
    assert response.json()["comment"] == (
        "Обновлённый комментарий"
    )


async def test_update_parent_with_duplicate_phone(
    client: AsyncClient,
    owner_headers: dict[str, str],
    parent: Parent,
    second_parent: Parent,
) -> None:
    """Проверяет запрет установки занятого телефона."""

    response = await client.patch(
        f"/api/v1/parents/{parent.id}",
        headers=owner_headers,
        json={"phone": second_parent.phone},
    )

    assert response.status_code == 409


async def test_branch_admin_can_access_parent_of_own_student(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    student: Student,
    parent: Parent,
) -> None:
    """Проверяет доступ администратора к родителю ученика филиала."""

    response = await client.get(
        f"/api/v1/parents/{parent.id}",
        headers=branch_admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == parent.id


async def test_other_branch_admin_cannot_access_parent(
    client: AsyncClient,
    second_branch_admin_headers: dict[str, str],
    student: Student,
    parent: Parent,
) -> None:
    """Проверяет запрет доступа администратора другого филиала."""

    response = await client.get(
        f"/api/v1/parents/{parent.id}",
        headers=second_branch_admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Нет доступа к этому родителю"