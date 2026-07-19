from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.dance_styles.model import DanceStyle
from app.modules.groups.model import Group, GroupMembership
from app.modules.students.model import Student
from app.modules.teachers.model import Teacher


async def test_owner_can_create_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group_payload: dict[str, Any],
    branch: Branch,
    teacher_profile: Teacher,
    dance_style: DanceStyle,
) -> None:
    """Проверяет создание группы руководителем."""

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json=group_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["name"] == group_payload["name"]
    assert data["max_students"] == group_payload["max_students"]
    assert data["students_count"] == 0
    assert data["students"] == []
    assert data["is_active"] is True

    assert data["branch"]["id"] == branch.id
    assert data["branch"]["name"] == branch.name

    assert data["dance_style"]["id"] == dance_style.id
    assert data["dance_style"]["name"] == dance_style.name

    assert data["teacher"]["id"] == teacher_profile.id
    assert data["teacher"]["first_name"] == teacher_profile.first_name
    assert data["teacher"]["last_name"] == teacher_profile.last_name

    assert "branch_id" not in data
    assert "teacher_id" not in data
    assert "dance_style_id" not in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_branch_admin_can_create_group_in_own_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    group_payload: dict[str, Any],
) -> None:
    """Проверяет создание группы администратором своего филиала."""

    response = await client.post(
        "/api/v1/groups",
        headers=branch_admin_headers,
        json=group_payload,
    )

    assert response.status_code == 201


async def test_branch_admin_cannot_create_group_in_other_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    group_payload: dict[str, Any],
    second_branch: Branch,
) -> None:
    """Проверяет запрет создания группы в чужом филиале."""

    group_payload["branch_id"] = second_branch.id

    response = await client.post(
        "/api/v1/groups",
        headers=branch_admin_headers,
        json=group_payload,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Нет доступа к этому филиалу"


async def test_create_group_without_authorization(
    client: AsyncClient,
    group_payload: dict[str, Any],
) -> None:
    """Проверяет защиту создания группы."""

    response = await client.post(
        "/api/v1/groups",
        json=group_payload,
    )

    assert response.status_code == 401


async def test_group_max_students_cannot_exceed_twenty_five(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group_payload: dict[str, Any],
) -> None:
    """Проверяет максимальную вместимость группы."""

    group_payload["max_students"] = 26

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json=group_payload,
    )

    assert response.status_code == 422


async def test_group_max_students_must_be_positive(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group_payload: dict[str, Any],
) -> None:
    """Проверяет минимальную вместимость группы."""

    group_payload["max_students"] = 0

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json=group_payload,
    )

    assert response.status_code == 422


async def test_cannot_create_duplicate_group_in_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
) -> None:
    """Проверяет уникальность названия группы внутри филиала."""

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json={
            "branch_id": group.branch_id,
            "dance_style_id": group.dance_style_id,
            "teacher_id": group.teacher_id,
            "name": group.name,
            "max_students": 20,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Группа с таким названием уже существует в филиале")


async def test_same_group_name_allowed_in_different_branches(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    second_branch: Branch,
    session: AsyncSession,
    dance_style: DanceStyle,
    teacher_profile: Teacher,
) -> None:
    """Разрешает одинаковое название группы в разных филиалах."""

    second_branch_group = Group(
        branch_id=second_branch.id,
        dance_style_id=dance_style.id,
        teacher_id=teacher_profile.id,
        name=group.name,
        max_students=20,
        is_active=True,
    )

    session.add(second_branch_group)
    await session.commit()

    assert second_branch_group.id is not None


async def test_cannot_create_group_with_nonexistent_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group_payload: dict[str, Any],
) -> None:
    """Проверяет создание группы с отсутствующим филиалом."""

    group_payload["branch_id"] = 999999

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json=group_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Филиал не найден"


async def test_cannot_create_group_with_nonexistent_teacher(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group_payload: dict[str, Any],
) -> None:
    """Проверяет создание группы с отсутствующим преподавателем."""

    group_payload["teacher_id"] = 999999

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json=group_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Преподаватель не найден"


async def test_cannot_create_group_with_nonexistent_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group_payload: dict[str, Any],
) -> None:
    """Проверяет создание группы с отсутствующим направлением."""

    group_payload["dance_style_id"] = 999999

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json=group_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Направление не найдено"


async def test_teacher_must_teach_group_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group_payload: dict[str, Any],
    second_dance_style: DanceStyle,
) -> None:
    """Проверяет соответствие направления преподавателю."""

    group_payload["dance_style_id"] = second_dance_style.id

    response = await client.post(
        "/api/v1/groups",
        headers=owner_headers,
        json=group_payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Преподаватель не ведёт выбранное направление")


async def test_owner_can_get_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
) -> None:
    """Проверяет получение группы по идентификатору."""

    response = await client.get(
        f"/api/v1/groups/{group.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == group.id
    assert data["name"] == group.name
    assert data["students_count"] == 0
    assert data["students"] == []


async def test_get_nonexistent_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрос отсутствующей группы."""

    response = await client.get(
        "/api/v1/groups/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Группа не найдена"


async def test_owner_can_get_groups(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
) -> None:
    """Проверяет получение списка групп."""

    response = await client.get(
        "/api/v1/groups",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == group.id


async def test_filter_groups_by_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    branch: Branch,
) -> None:
    """Проверяет фильтрацию групп по филиалу."""

    response = await client.get(
        "/api/v1/groups",
        headers=owner_headers,
        params={"branch_id": branch.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == group.id


async def test_filter_groups_by_teacher(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    teacher_profile: Teacher,
) -> None:
    """Проверяет фильтрацию групп по преподавателю."""

    response = await client.get(
        "/api/v1/groups",
        headers=owner_headers,
        params={"teacher_id": teacher_profile.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == group.id


async def test_filter_groups_by_dance_style(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    dance_style: DanceStyle,
) -> None:
    """Проверяет фильтрацию групп по направлению."""

    response = await client.get(
        "/api/v1/groups",
        headers=owner_headers,
        params={"dance_style_id": dance_style.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == group.id


async def test_search_groups_by_name(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
) -> None:
    """Проверяет поиск группы по названию."""

    response = await client.get(
        "/api/v1/groups",
        headers=owner_headers,
        params={"search": "Dancehall"},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == group.id


async def test_branch_admin_sees_only_own_branch_groups(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    group: Group,
    second_branch: Branch,
    dance_style: DanceStyle,
    teacher_profile: Teacher,
    session: AsyncSession,
) -> None:
    """Проверяет ограничение списка групп филиалом администратора."""

    other_group = Group(
        branch_id=second_branch.id,
        dance_style_id=dance_style.id,
        teacher_id=teacher_profile.id,
        name="Группа другого филиала",
        max_students=20,
        is_active=True,
    )

    session.add(other_group)
    await session.commit()

    response = await client.get(
        "/api/v1/groups",
        headers=branch_admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == group.id


async def test_owner_can_update_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
) -> None:
    """Проверяет обновление группы."""

    response = await client.patch(
        f"/api/v1/groups/{group.id}",
        headers=owner_headers,
        json={
            "name": "Обновлённая группа",
            "max_students": 15,
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Обновлённая группа"
    assert data["max_students"] == 15
    assert data["is_active"] is False


async def test_cannot_reduce_capacity_below_current_students_count(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
    second_student: Student,
    session: AsyncSession,
) -> None:
    """Проверяет запрет вместимости меньше текущего состава."""

    first_membership = GroupMembership(
        group_id=group.id,
        student_id=student.id,
        is_active=True,
        left_at=None,
    )
    second_membership = GroupMembership(
        group_id=group.id,
        student_id=second_student.id,
        is_active=True,
        left_at=None,
    )

    session.add_all(
        [
            first_membership,
            second_membership,
        ]
    )
    await session.commit()

    response = await client.patch(
        f"/api/v1/groups/{group.id}",
        headers=owner_headers,
        json={"max_students": 1},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Максимальное количество учеников не может быть " "меньше текущего состава группы"
    )


async def test_owner_can_add_student_to_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
) -> None:
    """Проверяет добавление ученика в группу."""

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": student.id},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["students_count"] == 1
    assert len(data["students"]) == 1
    assert data["students"][0]["student"]["id"] == student.id
    assert data["students"][0]["student"]["first_name"] == (student.first_name)
    assert data["students"][0]["student"]["last_name"] == (student.last_name)
    assert data["students"][0]["membership_id"] > 0
    assert "joined_at" in data["students"][0]


async def test_branch_admin_can_add_student_to_own_group(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    group: Group,
    student: Student,
) -> None:
    """Проверяет добавление ученика администратором филиала."""

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=branch_admin_headers,
        json={"student_id": student.id},
    )

    assert response.status_code == 200
    assert response.json()["students_count"] == 1


async def test_cannot_add_student_twice(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
    group_membership: GroupMembership,
) -> None:
    """Проверяет запрет повторного добавления ученика."""

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": student.id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Ученик уже состоит в этой группе")


async def test_cannot_add_nonexistent_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
) -> None:
    """Проверяет добавление отсутствующего ученика."""

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": 999999},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ученик не найден"


async def test_cannot_add_inactive_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    inactive_student: Student,
) -> None:
    """Проверяет запрет добавления неактивного ученика."""

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": inactive_student.id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("В группу можно добавить только активного ученика")


async def test_cannot_add_student_from_other_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    other_branch_student: Student,
) -> None:
    """Проверяет филиал ученика при добавлении в группу."""

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": other_branch_student.id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Ученик и группа относятся к разным филиалам")


async def test_cannot_add_student_to_inactive_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
    session: AsyncSession,
) -> None:
    """Проверяет запрет добавления в неактивную группу."""

    group.is_active = False
    await session.commit()

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": student.id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Нельзя добавить ученика в неактивную группу")


async def test_cannot_add_student_when_group_is_full(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
    second_student: Student,
    session: AsyncSession,
) -> None:
    """Проверяет ограничение вместимости группы."""

    group.max_students = 1

    membership = GroupMembership(
        group_id=group.id,
        student_id=student.id,
        is_active=True,
        left_at=None,
    )

    session.add(membership)
    await session.commit()

    response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": second_student.id},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("В группе достигнуто максимальное число учеников")


async def test_owner_can_remove_student_from_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
    group_membership: GroupMembership,
) -> None:
    """Проверяет исключение ученика из группы."""

    response = await client.delete(
        f"/api/v1/groups/{group.id}/students/{student.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["students_count"] == 0
    assert data["students"] == []


async def test_removed_membership_is_kept_in_database(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет сохранение истории членства после исключения."""

    response = await client.delete(
        f"/api/v1/groups/{group.id}/students/{student.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    await session.refresh(group_membership)

    assert group_membership.is_active is False
    assert group_membership.left_at is not None


async def test_cannot_remove_student_not_in_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
) -> None:
    """Проверяет исключение ученика, не состоящего в группе."""

    response = await client.delete(
        f"/api/v1/groups/{group.id}/students/{student.id}",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == ("Ученик не состоит в этой группе")


async def test_student_can_be_added_again_after_removal(
    client: AsyncClient,
    owner_headers: dict[str, str],
    group: Group,
    student: Student,
    group_membership: GroupMembership,
) -> None:
    """Проверяет повторное добавление ученика после исключения."""

    remove_response = await client.delete(
        f"/api/v1/groups/{group.id}/students/{student.id}",
        headers=owner_headers,
    )

    assert remove_response.status_code == 200

    add_response = await client.post(
        f"/api/v1/groups/{group.id}/students",
        headers=owner_headers,
        json={"student_id": student.id},
    )

    assert add_response.status_code == 200
    assert add_response.json()["students_count"] == 1
    assert add_response.json()["students"][0]["student"]["id"] == (student.id)
