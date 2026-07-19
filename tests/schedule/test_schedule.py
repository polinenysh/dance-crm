from typing import Any

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.groups.model import Group
from app.modules.halls.model import Hall
from app.modules.schedule.model import Lesson, ScheduleSlot
from app.shared.enums import LessonStatus


async def test_owner_can_create_schedule_slot(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
    group: Group,
    hall: Hall,
) -> None:
    """Проверяет создание шаблона расписания руководителем."""

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["weekday"] == schedule_slot_payload["weekday"]
    assert data["start_time"] == "18:00:00"
    assert data["end_time"] == "19:00:00"
    assert data["is_active"] is True

    assert data["group"]["id"] == group.id
    assert data["group"]["name"] == group.name

    assert data["hall"]["id"] == hall.id
    assert data["hall"]["name"] == hall.name
    assert data["hall"]["capacity"] == hall.capacity

    assert "group_id" not in data
    assert "hall_id" not in data
    assert "created_at" in data
    assert "updated_at" in data


async def test_branch_admin_can_create_slot_in_own_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
) -> None:
    """Проверяет создание расписания администратором филиала."""

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=branch_admin_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 201


async def test_create_schedule_slot_without_authorization(
    client: AsyncClient,
    schedule_slot_payload: dict[str, Any],
) -> None:
    """Проверяет защиту создания расписания."""

    response = await client.post(
        "/api/v1/schedule/slots",
        json=schedule_slot_payload,
    )

    assert response.status_code == 401


async def test_slot_end_time_must_be_after_start_time(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
) -> None:
    """Проверяет корректность временного диапазона."""

    schedule_slot_payload["start_time"] = "19:00:00"
    schedule_slot_payload["end_time"] = "18:00:00"

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 422


async def test_cannot_create_slot_for_nonexistent_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
) -> None:
    """Проверяет создание расписания для отсутствующей группы."""

    schedule_slot_payload["group_id"] = 999999

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Группа не найдена"


async def test_cannot_create_slot_for_nonexistent_hall(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
) -> None:
    """Проверяет создание расписания с отсутствующим залом."""

    schedule_slot_payload["hall_id"] = 999999

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Зал не найден"


async def test_cannot_create_slot_with_hall_from_other_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
    other_branch_hall: Hall,
) -> None:
    """Проверяет соответствие филиалов группы и зала."""

    schedule_slot_payload["hall_id"] = other_branch_hall.id

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Группа и зал относятся к разным филиалам"
    )


async def test_cannot_create_slot_in_inactive_hall(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
    inactive_hall: Hall,
) -> None:
    """Проверяет запрет использования неактивного зала."""

    schedule_slot_payload["hall_id"] = inactive_hall.id

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Нельзя использовать неактивный зал"
    )


async def test_hall_capacity_must_fit_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot_payload: dict[str, Any],
    hall: Hall,
    group: Group,
    session: AsyncSession,
) -> None:
    """Проверяет вместимость зала относительно группы."""

    hall.capacity = 10
    group.max_students = 20

    await session.commit()

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json=schedule_slot_payload,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Вместимость зала меньше вместимости группы"
    )


async def test_cannot_create_overlapping_slot_for_same_hall(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
    group: Group,
    hall: Hall,
) -> None:
    """Проверяет конфликт расписания по залу."""

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json={
            "group_id": group.id,
            "hall_id": hall.id,
            "weekday": schedule_slot.weekday,
            "start_time": "18:30:00",
            "end_time": "19:30:00",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Расписание пересекается по группе, залу "
        "или преподавателю"
    )


async def test_adjacent_schedule_slots_do_not_conflict(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
    group: Group,
    second_hall: Hall,
) -> None:
    """Проверяет отсутствие конфликта у соседних интервалов."""

    response = await client.post(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        json={
            "group_id": group.id,
            "hall_id": second_hall.id,
            "weekday": schedule_slot.weekday,
            "start_time": "19:00:00",
            "end_time": "20:00:00",
        },
    )

    assert response.status_code == 201


async def test_owner_can_get_schedule_slots(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
) -> None:
    """Проверяет получение списка шаблонов расписания."""

    response = await client.get(
        "/api/v1/schedule/slots",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == schedule_slot.id


async def test_filter_slots_by_group(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
    group: Group,
) -> None:
    """Проверяет фильтрацию расписания по группе."""

    response = await client.get(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        params={"group_id": group.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == schedule_slot.id


async def test_filter_slots_by_hall(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
    hall: Hall,
) -> None:
    """Проверяет фильтрацию расписания по залу."""

    response = await client.get(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        params={"hall_id": hall.id},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == schedule_slot.id


async def test_filter_only_active_slots(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
    session: AsyncSession,
) -> None:
    """Проверяет фильтрацию активных шаблонов расписания."""

    schedule_slot.is_active = False
    await session.commit()

    response = await client.get(
        "/api/v1/schedule/slots",
        headers=owner_headers,
        params={"active_only": True},
    )

    assert response.status_code == 200
    assert response.json() == []


async def test_owner_can_update_schedule_slot(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
    second_hall: Hall,
) -> None:
    """Проверяет обновление шаблона расписания."""

    response = await client.patch(
        f"/api/v1/schedule/slots/{schedule_slot.id}",
        headers=owner_headers,
        json={
            "hall_id": second_hall.id,
            "start_time": "19:00:00",
            "end_time": "20:00:00",
            "is_active": False,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["hall"]["id"] == second_hall.id
    assert data["start_time"] == "19:00:00"
    assert data["end_time"] == "20:00:00"
    assert data["is_active"] is False


async def test_generate_lessons_for_date_range(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
) -> None:
    """Проверяет генерацию занятий по шаблону."""

    response = await client.post(
        (
            f"/api/v1/schedule/slots/"
            f"{schedule_slot.id}/lessons/generate"
        ),
        headers=owner_headers,
        json={
            "date_from": "2026-07-20",
            "date_to": "2026-08-03",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert len(data) == 3

    assert [
        item["starts_at"][:10]
        for item in data
    ] == [
        "2026-07-20",
        "2026-07-27",
        "2026-08-03",
    ]

    assert all(
        item["status"] == "planned"
        for item in data
    )

    assert all(
        item["group"]["id"] == schedule_slot.group_id
        for item in data
    )

    assert all(
        item["hall"]["id"] == schedule_slot.hall_id
        for item in data
    )


async def test_generate_lessons_does_not_create_duplicates(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
) -> None:
    """Проверяет защиту от повторной генерации занятий."""

    payload = {
        "date_from": "2026-07-20",
        "date_to": "2026-07-27",
    }

    first_response = await client.post(
        (
            f"/api/v1/schedule/slots/"
            f"{schedule_slot.id}/lessons/generate"
        ),
        headers=owner_headers,
        json=payload,
    )

    second_response = await client.post(
        (
            f"/api/v1/schedule/slots/"
            f"{schedule_slot.id}/lessons/generate"
        ),
        headers=owner_headers,
        json=payload,
    )

    assert first_response.status_code == 201
    assert len(first_response.json()) == 2

    assert second_response.status_code == 201
    assert second_response.json() == []


async def test_cannot_generate_lessons_for_inactive_slot(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
    session: AsyncSession,
) -> None:
    """Проверяет генерацию по неактивному расписанию."""

    schedule_slot.is_active = False
    await session.commit()

    response = await client.post(
        (
            f"/api/v1/schedule/slots/"
            f"{schedule_slot.id}/lessons/generate"
        ),
        headers=owner_headers,
        json={
            "date_from": "2026-07-20",
            "date_to": "2026-07-27",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Нельзя создавать занятия по неактивному расписанию"
    )


async def test_lesson_generation_range_cannot_exceed_93_days(
    client: AsyncClient,
    owner_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
) -> None:
    """Проверяет максимальный диапазон генерации."""

    response = await client.post(
        (
            f"/api/v1/schedule/slots/"
            f"{schedule_slot.id}/lessons/generate"
        ),
        headers=owner_headers,
        json={
            "date_from": "2026-01-01",
            "date_to": "2026-12-31",
        },
    )

    assert response.status_code == 422


async def test_owner_can_get_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
) -> None:
    """Проверяет получение конкретного занятия."""

    response = await client.get(
        f"/api/v1/schedule/lessons/{lesson.id}",
        headers=owner_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == lesson.id
    assert data["schedule_slot_id"] == lesson.schedule_slot_id
    assert data["status"] == "planned"
    assert data["group"]["id"] == lesson.group_id
    assert data["hall"]["id"] == lesson.hall_id
    assert data["teacher"]["id"] == lesson.teacher_id


async def test_get_nonexistent_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет запрос отсутствующего занятия."""

    response = await client.get(
        "/api/v1/schedule/lessons/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Занятие не найдено"


async def test_get_lessons_by_date_range(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
) -> None:
    """Проверяет получение занятий за период."""

    response = await client.get(
        "/api/v1/schedule/lessons",
        headers=owner_headers,
        params={
            "date_from": "2026-07-20",
            "date_to": "2026-07-20",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == lesson.id


async def test_filter_lessons_by_status(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
) -> None:
    """Проверяет фильтрацию занятий по статусу."""

    response = await client.get(
        "/api/v1/schedule/lessons",
        headers=owner_headers,
        params={
            "date_from": "2026-07-20",
            "date_to": "2026-07-20",
            "status": "planned",
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == lesson.id


async def test_owner_can_cancel_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
) -> None:
    """Проверяет отмену занятия студией."""

    response = await client.post(
        f"/api/v1/schedule/lessons/{lesson.id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Преподаватель заболел",
            "cancelled_by_studio": True,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "cancelled"
    assert data["cancellation_reason"] == "Преподаватель заболел"
    assert data["cancelled_by_studio"] is True


async def test_cancel_reason_is_required(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
) -> None:
    """Проверяет обязательность причины отмены."""

    response = await client.post(
        f"/api/v1/schedule/lessons/{lesson.id}/cancel",
        headers=owner_headers,
        json={
            "reason": "",
            "cancelled_by_studio": True,
        },
    )

    assert response.status_code == 422


async def test_cannot_cancel_completed_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    session: AsyncSession,
) -> None:
    """Проверяет запрет отмены завершённого занятия."""

    lesson.status = LessonStatus.COMPLETED
    await session.commit()

    response = await client.post(
        f"/api/v1/schedule/lessons/{lesson.id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Отмена",
            "cancelled_by_studio": True,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Нельзя отменить завершённое занятие"
    )


async def test_branch_admin_sees_only_own_branch_slots(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    schedule_slot: ScheduleSlot,
) -> None:
    """Проверяет ограничение расписания филиалом администратора."""

    response = await client.get(
        "/api/v1/schedule/slots",
        headers=branch_admin_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == schedule_slot.id