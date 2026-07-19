from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.model import Attendance
from app.modules.groups.model import GroupMembership
from app.modules.schedule.model import Lesson
from app.modules.students.model import Student
from app.modules.subscriptions.model import StudentSubscription
from app.shared.enums import LessonStatus


async def make_lesson_finished(session: AsyncSession, lesson: Lesson) -> None:
    now = datetime.now(UTC)
    lesson.starts_at = now - timedelta(hours=2)
    lesson.ends_at = now - timedelta(hours=1)
    await session.commit()


async def test_owner_syncs_full_attendance_and_completes_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student: Student,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": [student.id]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["lesson_id"] == lesson.id
    assert data["students_count"] == 1
    assert data["attendances"][0]["student"]["id"] == student.id
    assert data["attendances"][0]["subscription_id"] == student_subscription.id
    await session.refresh(lesson)
    assert lesson.status == LessonStatus.COMPLETED
    assert lesson.completed_at is not None


async def test_branch_admin_can_sync_attendance_in_own_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    lesson: Lesson,
    student: Student,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=branch_admin_headers,
        json={"student_ids": [student.id]},
    )
    assert response.status_code == 200


async def test_sync_requires_authorization(
    client: AsyncClient,
    lesson: Lesson,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        json={"student_ids": []},
    )
    assert response.status_code == 401


async def test_full_list_removes_absent_student_and_returns_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student: Student,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    first = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": [student.id]},
    )
    assert first.status_code == 200
    second = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": []},
    )
    assert second.status_code == 200
    assert second.json()["students_count"] == 0
    result = await session.execute(select(Attendance).where(Attendance.lesson_id == lesson.id))
    assert result.scalars().all() == []


async def test_duplicate_student_ids_are_deduplicated(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student: Student,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": [student.id, student.id]},
    )
    assert response.status_code == 200
    assert response.json()["students_count"] == 1


async def test_cannot_complete_future_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
) -> None:
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": []},
    )
    assert response.status_code == 409


async def test_cannot_sync_cancelled_lesson(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    session: AsyncSession,
) -> None:
    lesson.status = LessonStatus.CANCELLED
    await session.commit()
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": []},
    )
    assert response.status_code == 409


async def test_attendance_can_be_edited_within_two_hours(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student: Student,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    first = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": []},
    )
    assert first.status_code == 200
    second = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": [student.id]},
    )
    assert second.status_code == 200
    assert second.json()["students_count"] == 1


async def test_attendance_cannot_be_edited_after_two_hours(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    lesson.status = LessonStatus.COMPLETED
    lesson.completed_at = datetime.now(UTC) - timedelta(hours=2, seconds=1)
    await session.commit()
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": []},
    )
    assert response.status_code == 409


async def test_student_must_be_active_group_member(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    second_student: Student,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": [second_student.id]},
    )
    assert response.status_code == 409


async def test_student_needs_valid_subscription(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    second_student: Student,
    group: object,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    membership = GroupMembership(group_id=lesson.group_id, student_id=second_student.id, is_active=True)
    session.add(membership)
    await session.commit()
    response = await client.put(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
        json={"student_ids": [second_student.id]},
    )
    assert response.status_code == 409


async def test_get_lesson_attendance(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    session: AsyncSession,
) -> None:
    await make_lesson_finished(session, lesson)
    response = await client.get(
        f"/api/v1/attendance/lessons/{lesson.id}",
        headers=owner_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"lesson_id": lesson.id, "students_count": 0, "attendances": []}
