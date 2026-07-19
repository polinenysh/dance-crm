from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.payments.enums import PaymentMethod, PaymentStatus
from app.modules.payments.model import Payment
from app.modules.students.model import Student
from app.modules.subscriptions.model import StudentSubscription
from app.modules.users.model import User

PAYMENTS_URL = "/api/v1/payments"


async def create_payment_request(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    student_id: int,
    branch_id: int,
    subscription_id: int | None = None,
    amount: int = 5000,
    payment_method: str = PaymentMethod.CASH.value,
    paid_at: datetime | None = None,
    comment: str | None = "Оплата абонемента",
) -> Response:
    """Отправляет запрос на создание оплаты."""

    payload: dict[str, Any] = {
        "student_id": student_id,
        "branch_id": branch_id,
        "subscription_id": subscription_id,
        "amount": amount,
        "payment_method": payment_method,
        "comment": comment,
    }

    if paid_at is not None:
        payload["paid_at"] = paid_at.isoformat()

    return await client.post(
        PAYMENTS_URL,
        headers=headers,
        json=payload,
    )


async def get_payment_data(
    session: AsyncSession,
    payment_id: int,
) -> dict[str, Any]:
    """Возвращает актуальные данные оплаты из базы данных."""

    result = await session.execute(
        select(
            Payment.id,
            Payment.student_id,
            Payment.branch_id,
            Payment.subscription_id,
            Payment.amount,
            Payment.payment_method,
            Payment.status,
            Payment.paid_at,
            Payment.comment,
            Payment.created_by,
            Payment.cancelled_at,
            Payment.cancelled_by,
            Payment.cancellation_reason,
            Payment.refunded_at,
            Payment.refunded_by,
            Payment.refund_reason,
        ).where(
            Payment.id == payment_id,
        )
    )

    row = result.mappings().one()

    return dict(row)


async def get_payment_count(
    session: AsyncSession,
    *,
    student_id: int | None = None,
    branch_id: int | None = None,
    status: PaymentStatus | None = None,
) -> int:
    """Возвращает количество оплат с указанными параметрами."""

    query = select(func.count(Payment.id))

    if student_id is not None:
        query = query.where(
            Payment.student_id == student_id,
        )

    if branch_id is not None:
        query = query.where(
            Payment.branch_id == branch_id,
        )

    if status is not None:
        query = query.where(
            Payment.status == status,
        )

    count = await session.scalar(query)

    return count or 0


@pytest.fixture
async def payment(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
    student_subscription: StudentSubscription,
    session: AsyncSession,
) -> dict[str, Any]:
    """Создаёт оплату для использования в тестах."""

    student_id = student.id
    branch_id = branch.id
    subscription_id = student_subscription.id

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        subscription_id=subscription_id,
        amount=5000,
        payment_method=PaymentMethod.CASH.value,
    )

    assert response.status_code == 201

    return response.json()


async def test_owner_can_create_cash_payment(
    client: AsyncClient,
    owner_headers: dict[str, str],
    owner: User,
    student: Student,
    branch: Branch,
    student_subscription: StudentSubscription,
    session: AsyncSession,
) -> None:
    """Проверяет создание наличной оплаты владельцем."""

    owner_id = owner.id
    student_id = student.id
    branch_id = branch.id
    subscription_id = student_subscription.id

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        subscription_id=subscription_id,
        amount=6000,
        payment_method=PaymentMethod.CASH.value,
        comment="Наличная оплата",
    )

    assert response.status_code == 201

    response_data = response.json()
    payment_id = response_data["id"]

    assert response_data["student_id"] == student_id
    assert response_data["branch_id"] == branch_id
    assert response_data["subscription_id"] == subscription_id
    assert response_data["amount"] == 6000
    assert response_data["payment_method"] == "cash"
    assert response_data["status"] == "completed"
    assert response_data["comment"] == "Наличная оплата"
    assert response_data["created_by"] == owner_id

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["student_id"] == student_id
    assert stored_payment["branch_id"] == branch_id
    assert stored_payment["subscription_id"] == subscription_id
    assert stored_payment["amount"] == 6000
    assert stored_payment["payment_method"] == PaymentMethod.CASH
    assert stored_payment["status"] == PaymentStatus.COMPLETED
    assert stored_payment["created_by"] == owner_id


async def test_owner_can_create_qr_code_payment(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
    student_subscription: StudentSubscription,
    session: AsyncSession,
) -> None:
    """Проверяет создание оплаты по QR-коду."""

    student_id = student.id
    branch_id = branch.id
    subscription_id = student_subscription.id

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        subscription_id=subscription_id,
        amount=5500,
        payment_method=PaymentMethod.QR_CODE.value,
    )

    assert response.status_code == 201

    response_data = response.json()
    payment_id = response_data["id"]

    assert response_data["payment_method"] == "qr_code"

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["payment_method"] == PaymentMethod.QR_CODE


async def test_payment_can_be_created_without_subscription(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
    session: AsyncSession,
) -> None:
    """Проверяет создание оплаты без привязки к абонементу."""

    student_id = student.id
    branch_id = branch.id

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        subscription_id=None,
        amount=1000,
        comment="Разовое занятие",
    )

    assert response.status_code == 201

    response_data = response.json()
    payment_id = response_data["id"]

    assert response_data["subscription_id"] is None

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["subscription_id"] is None


async def test_payment_uses_current_time_when_paid_at_is_missing(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
    session: AsyncSession,
) -> None:
    """Проверяет автоматическую установку времени оплаты."""

    student_id = student.id
    branch_id = branch.id

    before_request = datetime.now(UTC)

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        amount=1000,
    )

    after_request = datetime.now(UTC)

    assert response.status_code == 201

    paid_at = datetime.fromisoformat(response.json()["paid_at"].replace("Z", "+00:00"))

    assert before_request <= paid_at <= after_request


async def test_payment_accepts_explicit_paid_at(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
    session: AsyncSession,
) -> None:
    """Проверяет сохранение переданного времени оплаты."""

    student_id = student.id
    branch_id = branch.id
    paid_at = datetime.now(UTC) - timedelta(days=2)

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        amount=2000,
        paid_at=paid_at,
    )

    assert response.status_code == 201

    payment_id = response.json()["id"]

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["paid_at"] == paid_at


@pytest.mark.parametrize(
    "amount",
    [
        0,
        -1,
        -5000,
    ],
)
async def test_payment_amount_must_be_positive(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
    amount: int,
) -> None:
    """Проверяет валидацию положительной суммы."""

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student.id,
        branch_id=branch.id,
        amount=amount,
    )

    assert response.status_code == 422


async def test_unknown_payment_method_is_rejected(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
) -> None:
    """Проверяет запрет неизвестного способа оплаты."""

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student.id,
        branch_id=branch.id,
        amount=5000,
        payment_method="card",
    )

    assert response.status_code == 422


async def test_payment_for_nonexistent_student_returns_404(
    client: AsyncClient,
    owner_headers: dict[str, str],
    branch: Branch,
) -> None:
    """Проверяет ошибку при несуществующем ученике."""

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=999999,
        branch_id=branch.id,
        amount=5000,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ученик не найден"


async def test_payment_for_nonexistent_subscription_returns_404(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
) -> None:
    """Проверяет ошибку при несуществующем абонементе."""

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student.id,
        branch_id=branch.id,
        subscription_id=999999,
        amount=5000,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Абонемент не найден"


async def test_subscription_must_belong_to_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    second_student: Student,
    branch: Branch,
    student_subscription: StudentSubscription,
) -> None:
    """Проверяет принадлежность абонемента ученику."""

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=second_student.id,
        branch_id=branch.id,
        subscription_id=student_subscription.id,
        amount=5000,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Абонемент принадлежит другому ученику")


async def test_student_must_belong_to_selected_branch(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    second_branch: Branch,
) -> None:
    """Проверяет соответствие филиала ученика."""

    response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student.id,
        branch_id=second_branch.id,
        amount=5000,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Ученик относится к другому филиалу")


async def test_branch_admin_can_create_payment_in_own_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    branch_admin: User,
    student: Student,
    branch: Branch,
    student_subscription: StudentSubscription,
    session: AsyncSession,
) -> None:
    """Проверяет создание оплаты администратором филиала."""

    branch_admin_id = branch_admin.id
    student_id = student.id
    branch_id = branch.id
    subscription_id = student_subscription.id

    response = await create_payment_request(
        client=client,
        headers=branch_admin_headers,
        student_id=student_id,
        branch_id=branch_id,
        subscription_id=subscription_id,
        amount=5000,
    )

    assert response.status_code == 201

    payment_id = response.json()["id"]

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["created_by"] == branch_admin_id


async def test_branch_admin_cannot_create_payment_in_other_branch(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    student: Student,
    second_branch: Branch,
) -> None:
    """Проверяет запрет работы с чужим филиалом."""

    response = await create_payment_request(
        client=client,
        headers=branch_admin_headers,
        student_id=student.id,
        branch_id=second_branch.id,
        amount=5000,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == ("Нет доступа к этому филиалу")


async def test_owner_can_get_payment(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет получение оплаты по идентификатору."""

    payment_id = payment["id"]

    response = await client.get(
        f"{PAYMENTS_URL}/{payment_id}",
        headers=owner_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == payment_id


async def test_get_nonexistent_payment_returns_404(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    """Проверяет получение несуществующей оплаты."""

    response = await client.get(
        f"{PAYMENTS_URL}/999999",
        headers=owner_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Оплата не найдена"


async def test_completed_payment_can_be_updated(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Проверяет изменение проведённой оплаты."""

    payment_id = payment["id"]
    updated_paid_at = datetime.now(UTC) - timedelta(hours=3)

    response = await client.patch(
        f"{PAYMENTS_URL}/{payment_id}",
        headers=owner_headers,
        json={
            "payment_method": "qr_code",
            "paid_at": updated_paid_at.isoformat(),
            "comment": "Комментарий изменён",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["payment_method"] == "qr_code"
    assert response_data["comment"] == "Комментарий изменён"

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["payment_method"] == PaymentMethod.QR_CODE
    assert stored_payment["paid_at"] == updated_paid_at
    assert stored_payment["comment"] == "Комментарий изменён"


async def test_payment_amount_cannot_be_updated(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет отсутствие суммы в схеме изменения оплаты."""

    payment_id = payment["id"]

    response = await client.patch(
        f"{PAYMENTS_URL}/{payment_id}",
        headers=owner_headers,
        json={
            "amount": 100,
        },
    )

    assert response.status_code == 422


async def test_empty_payment_update_is_rejected(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет запрет пустого изменения."""

    payment_id = payment["id"]

    response = await client.patch(
        f"{PAYMENTS_URL}/{payment_id}",
        headers=owner_headers,
        json={},
    )

    assert response.status_code == 422


async def test_completed_payment_can_be_cancelled(
    client: AsyncClient,
    owner_headers: dict[str, str],
    owner: User,
    payment: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Проверяет отмену ошибочно созданной оплаты."""

    payment_id = payment["id"]
    owner_id = owner.id

    response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Оплата была добавлена дважды",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "cancelled"
    assert response_data["cancelled_by"] == owner_id
    assert response_data["cancelled_at"] is not None
    assert response_data["cancellation_reason"] == "Оплата была добавлена дважды"

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["status"] == PaymentStatus.CANCELLED
    assert stored_payment["cancelled_by"] == owner_id
    assert stored_payment["cancelled_at"] is not None
    assert stored_payment["cancellation_reason"] == "Оплата была добавлена дважды"


async def test_payment_cannot_be_cancelled_twice(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет защиту от повторной отмены."""

    payment_id = payment["id"]

    first_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Ошибочная оплата",
        },
    )

    assert first_response.status_code == 200

    second_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Повторная отмена",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == ("Оплата уже отменена")


async def test_cancelled_payment_cannot_be_updated(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет запрет изменения отменённой оплаты."""

    payment_id = payment["id"]

    cancel_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Ошибочная оплата",
        },
    )

    assert cancel_response.status_code == 200

    update_response = await client.patch(
        f"{PAYMENTS_URL}/{payment_id}",
        headers=owner_headers,
        json={
            "comment": "Новый комментарий",
        },
    )

    assert update_response.status_code == 409
    assert update_response.json()["detail"] == ("Можно изменять только проведённую оплату")


async def test_completed_payment_can_be_refunded(
    client: AsyncClient,
    owner_headers: dict[str, str],
    owner: User,
    payment: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Проверяет регистрацию возврата оплаты."""

    payment_id = payment["id"]
    owner_id = owner.id

    response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/refund",
        headers=owner_headers,
        json={
            "reason": "Клиент отказался от занятий",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["status"] == "refunded"
    assert response_data["refunded_by"] == owner_id
    assert response_data["refunded_at"] is not None
    assert response_data["refund_reason"] == "Клиент отказался от занятий"

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["status"] == PaymentStatus.REFUNDED
    assert stored_payment["refunded_by"] == owner_id
    assert stored_payment["refunded_at"] is not None
    assert stored_payment["refund_reason"] == "Клиент отказался от занятий"


async def test_payment_cannot_be_refunded_twice(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет защиту от повторного возврата."""

    payment_id = payment["id"]

    first_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/refund",
        headers=owner_headers,
        json={
            "reason": "Первый возврат",
        },
    )

    assert first_response.status_code == 200

    second_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/refund",
        headers=owner_headers,
        json={
            "reason": "Повторный возврат",
        },
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == ("Оплата уже возвращена")


async def test_cancelled_payment_cannot_be_refunded(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет запрет возврата отменённой оплаты."""

    payment_id = payment["id"]

    cancel_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Ошибочно создана",
        },
    )

    assert cancel_response.status_code == 200

    refund_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/refund",
        headers=owner_headers,
        json={
            "reason": "Попытка возврата",
        },
    )

    assert refund_response.status_code == 409
    assert refund_response.json()["detail"] == ("Отменённую оплату нельзя вернуть")


async def test_refunded_payment_cannot_be_cancelled(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет запрет отмены возвращённой оплаты."""

    payment_id = payment["id"]

    refund_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/refund",
        headers=owner_headers,
        json={
            "reason": "Возврат клиенту",
        },
    )

    assert refund_response.status_code == 200

    cancel_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Попытка отмены",
        },
    )

    assert cancel_response.status_code == 409
    assert cancel_response.json()["detail"] == ("Возвращённую оплату нельзя отменить")


async def test_list_payments_can_be_filtered_by_student(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
    student: Student,
) -> None:
    """Проверяет фильтрацию оплат по ученику."""

    student_id = student.id

    response = await client.get(
        PAYMENTS_URL,
        headers=owner_headers,
        params={
            "student_id": student_id,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] >= 1
    assert all(item["student_id"] == student_id for item in response_data["items"])


async def test_list_payments_can_be_filtered_by_status(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет фильтрацию оплат по статусу."""

    payment_id = payment["id"]

    cancel_response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Тестовая отмена",
        },
    )

    assert cancel_response.status_code == 200

    response = await client.get(
        PAYMENTS_URL,
        headers=owner_headers,
        params={
            "status": "cancelled",
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["total"] >= 1
    assert all(item["status"] == "cancelled" for item in response_data["items"])


async def test_payment_list_has_pagination(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
) -> None:
    """Проверяет параметры пагинации."""

    response = await client.get(
        PAYMENTS_URL,
        headers=owner_headers,
        params={
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["limit"] == 1
    assert response_data["offset"] == 0
    assert len(response_data["items"]) <= 1


async def test_branch_admin_sees_only_own_branch_payments(
    client: AsyncClient,
    branch_admin_headers: dict[str, str],
    payment: dict[str, Any],
    branch: Branch,
) -> None:
    """Проверяет ограничение списка оплат филиалом администратора."""

    branch_id = branch.id

    response = await client.get(
        PAYMENTS_URL,
        headers=branch_admin_headers,
    )

    assert response.status_code == 200

    response_data = response.json()

    assert all(item["branch_id"] == branch_id for item in response_data["items"])


async def test_summary_contains_payment_amounts_and_counts(
    client: AsyncClient,
    owner_headers: dict[str, str],
    student: Student,
    branch: Branch,
    session: AsyncSession,
) -> None:
    """Проверяет финансовую сводку по статусам."""

    student_id = student.id
    branch_id = branch.id

    first_response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        amount=5000,
    )

    second_response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        amount=3000,
        payment_method=PaymentMethod.QR_CODE.value,
    )

    third_response = await create_payment_request(
        client=client,
        headers=owner_headers,
        student_id=student_id,
        branch_id=branch_id,
        amount=2000,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert third_response.status_code == 201

    second_payment_id = second_response.json()["id"]
    third_payment_id = third_response.json()["id"]

    refund_response = await client.post(
        f"{PAYMENTS_URL}/{second_payment_id}/refund",
        headers=owner_headers,
        json={
            "reason": "Тестовый возврат",
        },
    )

    cancel_response = await client.post(
        f"{PAYMENTS_URL}/{third_payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Тестовая отмена",
        },
    )

    assert refund_response.status_code == 200
    assert cancel_response.status_code == 200

    response = await client.get(
        f"{PAYMENTS_URL}/summary",
        headers=owner_headers,
        params={
            "branch_id": branch_id,
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["completed_amount"] >= 5000
    assert response_data["refunded_amount"] >= 3000
    assert response_data["cancelled_amount"] >= 2000
    assert response_data["completed_count"] >= 1
    assert response_data["refunded_count"] >= 1
    assert response_data["cancelled_count"] >= 1


async def test_payment_is_not_physically_deleted_after_cancellation(
    client: AsyncClient,
    owner_headers: dict[str, str],
    payment: dict[str, Any],
    session: AsyncSession,
) -> None:
    """Проверяет сохранение финансовой записи после отмены."""

    payment_id = payment["id"]

    response = await client.post(
        f"{PAYMENTS_URL}/{payment_id}/cancel",
        headers=owner_headers,
        json={
            "reason": "Ошибка администратора",
        },
    )

    assert response.status_code == 200

    stored_payment = await get_payment_data(
        session=session,
        payment_id=payment_id,
    )

    assert stored_payment["id"] == payment_id
    assert stored_payment["status"] == PaymentStatus.CANCELLED
