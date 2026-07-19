from typing import Any

from httpx import AsyncClient

from app.modules.dance_styles.model import DanceStyle
from app.modules.teachers.model import Teacher


async def test_owner_can_create_teacher(
    client: AsyncClient,
    owner_headers: dict[str, str],
    dance_style: DanceStyle,
) -> None:
    response = await client.post(
        "/api/v1/teachers",
        headers=owner_headers,
        json={
            "first_name": "Елена",
            "last_name": "Смирнова",
            "phone": "+79990001122",
            "email": "elena@example.com",
            "dance_style_ids": [dance_style.id],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Елена"
    assert data["last_name"] == "Смирнова"
    assert data["dance_styles"][0]["id"] == dance_style.id
    assert "user" not in data
    assert "user_id" not in data


async def test_branch_admin_cannot_create_teacher(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    dance_style: DanceStyle,
) -> None:
    response = await client.post(
        "/api/v1/teachers",
        headers=branch_admin_headers,
        json={
            "first_name": "Елена",
            "last_name": "Смирнова",
            "dance_style_ids": [dance_style.id],
        },
    )
    assert response.status_code == 403


async def test_create_teacher_requires_authorization(
    client: AsyncClient,
    dance_style: DanceStyle,
) -> None:
    response = await client.post(
        "/api/v1/teachers",
        json={
            "first_name": "Елена",
            "last_name": "Смирнова",
            "dance_style_ids": [dance_style.id],
        },
    )
    assert response.status_code == 401


async def test_cannot_assign_nonexistent_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/teachers",
        headers=owner_headers,
        json={
            "first_name": "Елена",
            "last_name": "Смирнова",
            "dance_style_ids": [999999],
        },
    )
    assert response.status_code == 404


async def test_cannot_assign_inactive_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    inactive_dance_style: DanceStyle,
) -> None:
    response = await client.post(
        "/api/v1/teachers",
        headers=owner_headers,
        json={
            "first_name": "Елена",
            "last_name": "Смирнова",
            "dance_style_ids": [inactive_dance_style.id],
        },
    )
    assert response.status_code == 409


async def test_all_authenticated_users_can_get_teachers(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    teacher_profile: Teacher,
) -> None:
    response = await client.get(
        "/api/v1/teachers",
        headers=branch_admin_headers,
    )
    assert response.status_code == 200
    assert response.json()[0]["id"] == teacher_profile.id


async def test_get_teachers_requires_authorization(client: AsyncClient) -> None:
    response = await client.get("/api/v1/teachers")
    assert response.status_code == 401


async def test_get_teacher_by_id(
    client: AsyncClient,
    owner_headers: dict[str, str],
    teacher_profile: Teacher,
) -> None:
    response = await client.get(
        f"/api/v1/teachers/{teacher_profile.id}",
        headers=owner_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == teacher_profile.id
    assert data["first_name"] == teacher_profile.first_name
    assert data["last_name"] == teacher_profile.last_name


async def test_filter_teachers_by_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    teacher_profile: Teacher,
    dance_style: DanceStyle,
) -> None:
    response = await client.get(
        "/api/v1/teachers",
        headers=owner_headers,
        params={"dance_style_id": dance_style.id},
    )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [teacher_profile.id]


async def test_search_teachers_by_name(
    client: AsyncClient,
    owner_headers: dict[str, str],
    teacher_profile: Teacher,
) -> None:
    response = await client.get(
        "/api/v1/teachers",
        headers=owner_headers,
        params={"search": "Иванова"},
    )
    assert response.status_code == 200
    assert response.json()[0]["id"] == teacher_profile.id


async def test_owner_can_update_teacher(
    client: AsyncClient,
    owner_headers: dict[str, str],
    teacher_profile: Teacher,
) -> None:
    response = await client.patch(
        f"/api/v1/teachers/{teacher_profile.id}",
        headers=owner_headers,
        json={"first_name": "Марина", "is_active": False},
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Марина"
    assert response.json()["is_active"] is False


async def test_branch_admin_cannot_update_teacher(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    teacher_profile: Teacher,
) -> None:
    response = await client.patch(
        f"/api/v1/teachers/{teacher_profile.id}",
        headers=branch_admin_headers,
        json={"first_name": "Марина"},
    )
    assert response.status_code == 403
