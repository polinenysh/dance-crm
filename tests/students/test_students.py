from datetime import date
from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.parents.model import Parent
from app.modules.students.model import Student
from app.modules.users.model import User
from app.shared.enums import StudentStatus


async def test_owner_can_create_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student_payload: dict[str, Any],
    parent: Parent,
    branch: Branch,
) -> None:
    """Проверяет создание ученика и вложенные связи."""

    response = await client.post(
        "/api/v1/students",
        headers=owner_headers,
        json=student_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["first_name"] == student_payload["first_name"]
    assert data["last_name"] == student_payload["last_name"]
    assert data["birth_date"] == student_payload["birth_date"]
    assert data["status"] == "active"

    assert "parent_id" not in data
    assert "branch_id" not in data
    assert "created_by" not in data

    assert data["parent"] == {
        "id": parent.id,
        "first_name": parent.first_name,
        "last_name": parent.last_name,
        "phone": parent.phone,
    }

    assert data["branch"] == {
        "id": branch.id,
        "name": branch.name,
        "address": branch.address,
    }


async def test_create_student_without_birth_date(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student_payload: dict[str, Any],
) -> None:
    """Проверяет создание ученика без даты рождения."""

    student_payload["birth_date"] = None

    response = await client.post(
        "/api/v1/students",
        headers=owner_headers,
        json=student_payload,
    )

    assert response.status_code == 201
    assert response.json()["birth_date"] is None


async def test_create_student_with_future_birth_date(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student_payload: dict[str, Any],
) -> None:
    """Проверяет запрет будущей даты рождения."""

    student_payload["birth_date"] = "2099-01-01"

    response = await client.post(
        "/api/v1/students",
        headers=owner_headers,
        json=student_payload,
    )

    assert response.status_code == 422


async def test_create_student_for_nonexistent_parent(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student_payload: dict[str, Any],
) -> None:
    """Проверяет запрет создания без существующего родителя."""

    student_payload["parent_id"] = 999999

    response = await client.post(
        "/api/v1/students",
        headers=owner_headers,
        json=student_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Родитель не найден"


async def test_create_student_for_nonexistent_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student_payload: dict[str, Any],
) -> None:
    """Проверяет запрет создания без существующего филиала."""

    student_payload["branch_id"] = 999999

    response = await client.post(
        "/api/v1/students",
        headers=owner_headers,
        json=student_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Филиал не найден"


async def test_create_student_for_inactive_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student_payload: dict[str, Any],
    branch: Branch,
    session: AsyncSession,
) -> None:
    """Проверяет запрет добавления в неактивный филиал."""

    branch.is_active = False
    await session.commit()

    response = await client.post(
        "/api/v1/students",
        headers=owner_headers,
        json=student_payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Нельзя добавить ученика в неактивный филиал"
    )


async def test_branch_admin_can_create_student_in_own_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    student_payload: dict[str, Any],
) -> None:
    """Проверяет создание ученика администратором своего филиала."""

    response = await client.post(
        "/api/v1/students",
        headers=branch_admin_headers,
        json=student_payload,
    )

    assert response.status_code == 201


async def test_branch_admin_cannot_create_student_in_other_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    student_payload: dict[str, Any],
    second_branch: Branch,
) -> None:
    """Проверяет запрет создания ученика в другом филиале."""

    student_payload["branch_id"] = second_branch.id

    response = await client.post(
        "/api/v1/students",
        headers=branch_admin_headers,
        json=student_payload,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Нет доступа к этому филиалу"


async def test_owner_can_get_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    parent: Parent,
    branch: Branch,
) -> None:
    """Проверяет получение ученика со связанными данными."""

    response = await client.get(
        f"/api/v1/students/{student.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == student.id
    assert data["parent"]["id"] == parent.id
    assert data["parent"]["first_name"] == parent.first_name
    assert data["parent"]["last_name"] == parent.last_name
    assert data["parent"]["phone"] == parent.phone
    assert data["branch"]["id"] == branch.id
    assert data["branch"]["name"] == branch.name
    assert data["branch"]["address"] == branch.address


async def test_get_nonexistent_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет ошибку для отсутствующего ученика."""

    response = await client.get(
        "/api/v1/students/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ученик не найден"


async def test_owner_can_get_students(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
) -> None:
    """Проверяет получение списка учеников."""

    response = await client.get(
        "/api/v1/students",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == student.id


async def test_filter_students_by_parent(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    parent: Parent,
) -> None:
    """Проверяет фильтрацию учеников по родителю."""

    response = await client.get(
        "/api/v1/students",
        headers=owner_headers,
        params={"parent_id": parent.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == student.id


async def test_filter_students_by_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
) -> None:
    """Проверяет фильтрацию учеников по филиалу."""

    response = await client.get(
        "/api/v1/students",
        headers=owner_headers,
        params={"branch_id": branch.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["branch"]["id"] == branch.id


async def test_filter_students_by_status(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
) -> None:
    """Проверяет фильтрацию учеников по статусу."""

    response = await client.get(
        "/api/v1/students",
        headers=owner_headers,
        params={"status": "active"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == student.id


async def test_search_students_by_name(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
) -> None:
    """Проверяет поиск ученика по имени."""

    response = await client.get(
        "/api/v1/students",
        headers=owner_headers,
        params={"search": student.first_name},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == student.id


async def test_owner_can_update_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
) -> None:
    """Проверяет обновление данных ученика."""

    response = await client.patch(
        f"/api/v1/students/{student.id}",
        headers=owner_headers,
        json={
            "first_name": "Екатерина",
            "birth_date": None,
            "comment": "Обновлённая карточка",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["first_name"] == "Екатерина"
    assert data["birth_date"] is None
    assert data["comment"] == "Обновлённая карточка"
    assert "parent" in data
    assert "branch" in data


async def test_owner_can_change_student_parent(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    second_parent: Parent,
) -> None:
    """Проверяет изменение родителя ученика."""

    response = await client.patch(
        f"/api/v1/students/{student.id}",
        headers=owner_headers,
        json={"parent_id": second_parent.id},
    )

    assert response.status_code == 200
    assert response.json()["parent"]["id"] == second_parent.id
    assert response.json()["parent"]["first_name"] == (
        second_parent.first_name
    )
    assert response.json()["parent"]["last_name"] == (
        second_parent.last_name
    )
    assert response.json()["parent"]["phone"] == second_parent.phone


async def test_archive_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
) -> None:
    """Проверяет архивирование ученика."""

    response = await client.post(
        f"/api/v1/students/{student.id}/archive",
        headers=owner_headers,
        json={
            "comment": "Завершил обучение",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "archived"
    assert data["comment"] == "Завершил обучение"
    assert data["parent"]["id"] == student.parent_id
    assert data["branch"]["id"] == student.branch_id


async def test_branch_admin_sees_only_own_branch_students(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    session: AsyncSession,
    student: Student,
    second_branch: Branch,
    second_parent: Parent,
    owner: User,
) -> None:
    """Проверяет ограничение списка учеников филиалом администратора."""

    other_student = Student(
        parent_id=second_parent.id,
        branch_id=second_branch.id,
        first_name="Александр",
        last_name="Петров",
        birth_date=date(2018, 4, 15),
        status=StudentStatus.ACTIVE,
        comment=None,
        created_by=owner.id,
    )

    session.add(other_student)
    await session.commit()
    await session.refresh(other_student)

    response = await client.get(
        "/api/v1/students",
        headers=branch_admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == student.id


async def test_other_branch_admin_cannot_get_student(
    client: AsyncClient,
    second_branch_admin_headers: dict[str, str],
    student: Student,
) -> None:
    """Проверяет запрет доступа к ученику другого филиала."""

    response = await client.get(
        f"/api/v1/students/{student.id}",
        headers=second_branch_admin_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Нет доступа к этому филиалу"