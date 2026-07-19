from datetime import date

from app.modules.subscriptions.service import (
    student_subscription_service,
)


def test_calculate_expiration_date_for_regular_month() -> None:
    """Проверяет фиксированный срок абонемента в 30 дней."""

    result = student_subscription_service.calculate_expiration_date(
        date(2026, 7, 1),
    )

    assert result == date(2026, 7, 30)


def test_calculate_expiration_date_for_february() -> None:
    """Проверяет, что февраль не сокращает срок абонемента."""

    result = student_subscription_service.calculate_expiration_date(
        date(2026, 2, 1),
    )

    assert result == date(2026, 3, 2)


def test_calculate_expiration_date_from_january_31() -> None:
    """Проверяет расчёт от последнего дня января."""

    result = student_subscription_service.calculate_expiration_date(
        date(2026, 1, 31),
    )

    assert result == date(2026, 3, 1)


def test_subscription_duration_is_thirty_inclusive_days() -> None:
    """Проверяет 30 дней с учётом обеих граничных дат."""

    starts_on = date(2026, 2, 1)

    expires_on = (
        student_subscription_service.calculate_expiration_date(
            starts_on,
        )
    )

    assert (expires_on - starts_on).days + 1 == 30