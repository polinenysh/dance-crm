from datetime import timedelta
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.groups.model import GroupMembership
from app.modules.schedule.model import Lesson
from app.modules.subscriptions.model import (
    StudentSubscription,
    SubscriptionExtension,
)
from app.modules.users.model import User
from app.shared.enums import LessonStatus


async def cancel_lesson(
    client: AsyncClient,
    lesson_id: int,
    headers: dict[str, str],
    *,
    cancelled_by_studio: bool = True,
    reason: str = "Преподаватель заболел",
) -> Response:
    """Отменяет занятие через API."""

    return await client.post(
        f"/api/v1/schedule/lessons/{lesson_id}/cancel",
        headers=headers,
        json={
            "reason": reason,
            "cancelled_by_studio": cancelled_by_studio,
        },
    )


async def get_subscription_data(
    session: AsyncSession,
    subscription_id: int,
) -> dict[str, Any]:
    """Возвращает актуальные данные абонемента из базы данных."""

    result = await session.execute(
        select(
            StudentSubscription.id,
            StudentSubscription.student_id,
            StudentSubscription.branch_id,
            StudentSubscription.starts_on,
            StudentSubscription.expires_on,
            StudentSubscription.extension_days,
        ).where(
            StudentSubscription.id == subscription_id,
        )
    )

    row = result.mappings().one()

    return dict(row)


async def get_extension_data(
    session: AsyncSession,
    subscription_id: int,
    lesson_id: int,
) -> dict[str, Any] | None:
    """Возвращает данные продления для абонемента и занятия."""

    result = await session.execute(
        select(
            SubscriptionExtension.id,
            SubscriptionExtension.subscription_id,
            SubscriptionExtension.lesson_id,
            SubscriptionExtension.days,
            SubscriptionExtension.reason,
            SubscriptionExtension.created_by,
        ).where(
            SubscriptionExtension.subscription_id == subscription_id,
            SubscriptionExtension.lesson_id == lesson_id,
        )
    )

    row = result.mappings().one_or_none()

    if row is None:
        return None

    return dict(row)


async def get_lesson_status(
    session: AsyncSession,
    lesson_id: int,
) -> LessonStatus | None:
    """Возвращает актуальный статус занятия."""

    return await session.scalar(
        select(Lesson.status).where(
            Lesson.id == lesson_id,
        )
    )


async def get_extensions_count(
    session: AsyncSession,
    lesson_id: int,
    subscription_id: int | None = None,
) -> int:
    """Возвращает количество записей о продлении."""

    query = select(
        func.count(SubscriptionExtension.id)
    ).where(
        SubscriptionExtension.lesson_id == lesson_id,
    )

    if subscription_id is not None:
        query = query.where(
            SubscriptionExtension.subscription_id == subscription_id,
        )

    count = await session.scalar(query)

    return count or 0


async def test_studio_cancellation_extends_subscription_by_seven_days(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет продление абонемента на семь дней."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == (
        previous_expires_on + timedelta(days=7)
    )
    assert updated_subscription["extension_days"] == (
        previous_extension_days + 7
    )


async def test_studio_cancellation_creates_extension_history(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    owner: User,
    session: AsyncSession,
) -> None:
    """Проверяет создание записи об автоматическом продлении."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    owner_id = owner.id

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
        reason="Зал временно закрыт",
    )

    assert response.status_code == 200

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is not None
    assert extension["subscription_id"] == subscription_id
    assert extension["lesson_id"] == lesson_id
    assert extension["days"] == 7
    assert extension["reason"] == "Отмена занятия студией"
    assert extension["created_by"] == owner_id


async def test_cancellation_not_by_studio_does_not_extend_subscription(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет отсутствие продления при отмене не студией."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
        cancelled_by_studio=False,
        reason="Отмена не по инициативе студии",
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == previous_expires_on
    assert (
        updated_subscription["extension_days"]
        == previous_extension_days
    )

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is None


async def test_repeated_cancellation_does_not_extend_twice(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет защиту от повторного продления."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    first_response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert first_response.status_code == 200

    second_response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Занятие уже отменено"

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == (
        previous_expires_on + timedelta(days=7)
    )
    assert updated_subscription["extension_days"] == (
        previous_extension_days + 7
    )

    extensions_count = await get_extensions_count(
        session=session,
        lesson_id=lesson_id,
        subscription_id=subscription_id,
    )

    assert extensions_count == 1


async def test_inactive_group_member_subscription_is_not_extended(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет отсутствие продления у неактивного участника."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    group_membership.is_active = False
    await session.commit()

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == previous_expires_on
    assert (
        updated_subscription["extension_days"]
        == previous_extension_days
    )

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is None


async def test_student_without_subscription_does_not_block_cancellation(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет отмену при отсутствии абонемента у ученика."""

    lesson_id = lesson.id

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    stored_status = await get_lesson_status(
        session=session,
        lesson_id=lesson_id,
    )

    assert stored_status == LessonStatus.CANCELLED

    extensions_count = await get_extensions_count(
        session=session,
        lesson_id=lesson_id,
    )

    assert extensions_count == 0


async def test_expired_subscription_is_not_extended(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет отсутствие продления истёкшего абонемента."""

    lesson_id = lesson.id
    lesson_date = lesson.starts_at.date()
    subscription_id = student_subscription.id

    student_subscription.starts_on = (
        lesson_date - timedelta(days=40)
    )
    student_subscription.expires_on = (
        lesson_date - timedelta(days=1)
    )

    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    await session.commit()

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == previous_expires_on
    assert (
        updated_subscription["extension_days"]
        == previous_extension_days
    )

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is None


async def test_future_subscription_is_not_selected_as_current(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет отсутствие продления ещё не начавшегося абонемента."""

    lesson_id = lesson.id
    lesson_date = lesson.starts_at.date()
    subscription_id = student_subscription.id

    student_subscription.starts_on = (
        lesson_date + timedelta(days=1)
    )
    student_subscription.expires_on = (
        lesson_date + timedelta(days=30)
    )

    previous_starts_on = student_subscription.starts_on
    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    await session.commit()

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["starts_on"] == previous_starts_on
    assert updated_subscription["expires_on"] == previous_expires_on
    assert (
        updated_subscription["extension_days"]
        == previous_extension_days
    )

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is None


async def test_subscription_is_extended_on_its_start_date(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет продление в первый день действия абонемента."""

    lesson_id = lesson.id
    lesson_date = lesson.starts_at.date()
    subscription_id = student_subscription.id

    student_subscription.starts_on = lesson_date
    student_subscription.expires_on = (
        lesson_date + timedelta(days=29)
    )

    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    await session.commit()

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == (
        previous_expires_on + timedelta(days=7)
    )
    assert updated_subscription["extension_days"] == (
        previous_extension_days + 7
    )


async def test_subscription_is_extended_on_its_expiration_date(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет продление в последний день действия абонемента."""

    lesson_id = lesson.id
    lesson_date = lesson.starts_at.date()
    subscription_id = student_subscription.id

    student_subscription.starts_on = (
        lesson_date - timedelta(days=29)
    )
    student_subscription.expires_on = lesson_date

    previous_extension_days = student_subscription.extension_days

    await session.commit()

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == (
        lesson_date + timedelta(days=7)
    )
    assert updated_subscription["extension_days"] == (
        previous_extension_days + 7
    )


async def test_following_subscription_is_shifted_by_seven_days(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    following_student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет перенос следующего абонемента."""

    lesson_id = lesson.id
    current_subscription_id = student_subscription.id
    following_subscription_id = following_student_subscription.id

    current_previous_expires_on = student_subscription.expires_on
    following_previous_starts_on = (
        following_student_subscription.starts_on
    )
    following_previous_expires_on = (
        following_student_subscription.expires_on
    )

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_current = await get_subscription_data(
        session=session,
        subscription_id=current_subscription_id,
    )

    updated_following = await get_subscription_data(
        session=session,
        subscription_id=following_subscription_id,
    )

    assert updated_current["expires_on"] == (
        current_previous_expires_on + timedelta(days=7)
    )
    assert updated_following["starts_on"] == (
        following_previous_starts_on + timedelta(days=7)
    )
    assert updated_following["expires_on"] == (
        following_previous_expires_on + timedelta(days=7)
    )


async def test_following_subscription_extension_days_are_not_changed(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    following_student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет, что перенос не считается продлением следующего абонемента."""

    lesson_id = lesson.id
    following_subscription_id = following_student_subscription.id
    previous_extension_days = (
        following_student_subscription.extension_days
    )

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_following = await get_subscription_data(
        session=session,
        subscription_id=following_subscription_id,
    )

    assert (
        updated_following["extension_days"]
        == previous_extension_days
    )


async def test_all_following_subscriptions_are_shifted(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    following_student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    owner: User,
    session: AsyncSession,
) -> None:
    """Проверяет перенос всей цепочки будущих абонементов."""

    lesson_id = lesson.id
    owner_id = owner.id

    student_id = student_subscription.student_id
    plan_id = student_subscription.plan_id
    branch_id = student_subscription.branch_id
    lessons_count = student_subscription.lessons_count
    price = student_subscription.price

    second_id = following_student_subscription.id
    second_previous_starts_on = (
        following_student_subscription.starts_on
    )
    second_previous_expires_on = (
        following_student_subscription.expires_on
    )

    third_subscription = StudentSubscription(
        student_id=student_id,
        plan_id=plan_id,
        branch_id=branch_id,
        starts_on=(
            second_previous_expires_on + timedelta(days=1)
        ),
        expires_on=(
            second_previous_expires_on + timedelta(days=30)
        ),
        lessons_count=lessons_count,
        price=price,
        extension_days=0,
        comment=None,
        created_by=owner_id,
    )

    session.add(third_subscription)
    await session.commit()
    await session.refresh(third_subscription)

    third_id = third_subscription.id
    third_previous_starts_on = third_subscription.starts_on
    third_previous_expires_on = third_subscription.expires_on

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_second = await get_subscription_data(
        session=session,
        subscription_id=second_id,
    )

    updated_third = await get_subscription_data(
        session=session,
        subscription_id=third_id,
    )

    assert updated_second["starts_on"] == (
        second_previous_starts_on + timedelta(days=7)
    )
    assert updated_second["expires_on"] == (
        second_previous_expires_on + timedelta(days=7)
    )
    assert updated_third["starts_on"] == (
        third_previous_starts_on + timedelta(days=7)
    )
    assert updated_third["expires_on"] == (
        third_previous_expires_on + timedelta(days=7)
    )


async def test_subscription_from_other_branch_is_not_extended(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    second_branch: Branch,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет соответствие филиала абонемента занятию."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    second_branch_id = second_branch.id
    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    student_subscription.branch_id = second_branch_id
    await session.commit()

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == previous_expires_on
    assert (
        updated_subscription["extension_days"]
        == previous_extension_days
    )

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is None


async def test_multiple_students_receive_extensions(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    second_student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    second_group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет продление абонементов всех участников группы."""

    lesson_id = lesson.id
    first_subscription_id = student_subscription.id
    second_subscription_id = second_student_subscription.id

    first_previous_expires_on = student_subscription.expires_on
    second_previous_expires_on = (
        second_student_subscription.expires_on
    )

    first_previous_extension_days = (
        student_subscription.extension_days
    )
    second_previous_extension_days = (
        second_student_subscription.extension_days
    )

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 200

    updated_first = await get_subscription_data(
        session=session,
        subscription_id=first_subscription_id,
    )

    updated_second = await get_subscription_data(
        session=session,
        subscription_id=second_subscription_id,
    )

    assert updated_first["expires_on"] == (
        first_previous_expires_on + timedelta(days=7)
    )
    assert updated_second["expires_on"] == (
        second_previous_expires_on + timedelta(days=7)
    )

    assert updated_first["extension_days"] == (
        first_previous_extension_days + 7
    )
    assert updated_second["extension_days"] == (
        second_previous_extension_days + 7
    )

    extensions_count = await get_extensions_count(
        session=session,
        lesson_id=lesson_id,
    )

    assert extensions_count == 2


async def test_completed_lesson_cannot_be_cancelled_or_extended(
    client: AsyncClient,
    owner_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    session: AsyncSession,
) -> None:
    """Проверяет запрет отмены завершённого занятия."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    lesson.status = LessonStatus.COMPLETED
    await session.commit()

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=owner_headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Нельзя отменить завершённое занятие"
    )

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == previous_expires_on
    assert (
        updated_subscription["extension_days"]
        == previous_extension_days
    )

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is None


async def test_branch_admin_can_cancel_and_extend_subscription(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    lesson: Lesson,
    student_subscription: StudentSubscription,
    group_membership: GroupMembership,
    branch_admin: User,
    session: AsyncSession,
) -> None:
    """Проверяет продление при отмене администратором филиала."""

    lesson_id = lesson.id
    subscription_id = student_subscription.id
    branch_admin_id = branch_admin.id

    previous_expires_on = student_subscription.expires_on
    previous_extension_days = student_subscription.extension_days

    response = await cancel_lesson(
        client=client,
        lesson_id=lesson_id,
        headers=branch_admin_headers,
    )

    assert response.status_code == 200

    updated_subscription = await get_subscription_data(
        session=session,
        subscription_id=subscription_id,
    )

    assert updated_subscription["expires_on"] == (
        previous_expires_on + timedelta(days=7)
    )
    assert updated_subscription["extension_days"] == (
        previous_extension_days + 7
    )

    extension = await get_extension_data(
        session=session,
        subscription_id=subscription_id,
        lesson_id=lesson_id,
    )

    assert extension is not None
    assert extension["created_by"] == branch_admin_id