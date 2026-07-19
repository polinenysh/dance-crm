from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from app.modules.reports.service import ReportService, _percent


def test_percent_handles_zero_denominator() -> None:
    assert _percent(10, 0) == 0.0


def test_percent_rounds_to_two_decimal_places() -> None:
    assert _percent(2, 3) == 66.67


@pytest.mark.asyncio
async def test_get_revenue_builds_report() -> None:
    repository = AsyncMock()
    repository.revenue.return_value = {
        "total": 4500,
        "payments_count": 3,
        "branches": [(1, "Центральный", 4500, 3)],
        "daily": [(date(2026, 7, 10), 4500, 3)],
    }
    service = ReportService(repository)

    report = await service.get_revenue(
        AsyncMock(),
        date(2026, 7, 1),
        date(2026, 7, 31),
        None,
    )

    assert report.total == 4500
    assert report.payments_count == 3
    assert report.branches[0].branch_name == "Центральный"
    assert report.daily[0].revenue == 4500


@pytest.mark.asyncio
async def test_get_groups_calculates_occupancy() -> None:
    repository = AsyncMock()
    repository.groups.return_value = [
        (1, "Dancehall Kids", 1, "Центральный", 2, "Мария", "Иванова", 20, True, 15),
        (2, "Hip-Hop Kids", 1, "Центральный", 3, "Анна", "Петрова", 10, False, 5),
    ]
    repository.group_students_count.return_value = 18
    service = ReportService(repository)

    report = await service.get_groups(AsyncMock(), 1)

    assert report.groups_count == 2
    assert report.active_groups_count == 1
    assert report.unique_students_count == 18
    assert report.average_occupancy_percent == 66.67
    assert report.groups[0].available_places == 5
    assert report.groups[0].occupancy_percent == 75.0


@pytest.mark.asyncio
async def test_get_attendance_calculates_average() -> None:
    repository = AsyncMock()
    repository.attendance.return_value = {
        "completed_lessons": 2,
        "cancelled_lessons": 1,
        "groups": [
            (1, "Dancehall Kids", 2, 20, 15),
            (2, "Hip-Hop Kids", 1, 10, 5),
        ],
    }
    service = ReportService(repository)

    report = await service.get_attendance(
        AsyncMock(),
        date(2026, 7, 1),
        date(2026, 7, 31),
        1,
    )

    assert report.completed_lessons == 2
    assert report.cancelled_lessons == 1
    assert report.expected_visits == 30
    assert report.actual_visits == 20
    assert report.average_attendance_percent == 66.67


@pytest.mark.asyncio
async def test_get_subscriptions_calculates_remaining_lessons() -> None:
    repository = AsyncMock()
    today = date.today()
    repository.subscriptions.return_value = {
        "active": 1,
        "upcoming": 0,
        "expired": 0,
        "expiring_soon": 1,
        "unpaid": 0,
        "items": [
            (
                10,
                20,
                "Мария",
                "Иванова",
                1,
                "Центральный",
                5,
                "8 занятий",
                today - timedelta(days=20),
                today + timedelta(days=3),
                8,
                6,
                1,
            )
        ],
    }
    service = ReportService(repository)

    report = await service.get_subscriptions(AsyncMock(), 1, 7, False)

    assert report.active == 1
    assert report.expiring_soon == 1
    assert report.items[0].lessons_remaining == 2
    assert report.items[0].days_until_expiration == 3
    assert report.items[0].is_paid is True


@pytest.mark.asyncio
async def test_dashboard_combines_all_reports() -> None:
    repository = AsyncMock()
    repository.revenue.return_value = {
        "total": 10000,
        "payments_count": 2,
        "branches": [],
        "daily": [],
    }
    repository.attendance.return_value = {
        "completed_lessons": 2,
        "cancelled_lessons": 1,
        "groups": [(1, "Группа", 2, 10, 8)],
    }
    repository.groups.return_value = [(1, "Группа", 1, "Центральный", 1, "Мария", "Иванова", 20, True, 10)]
    repository.group_students_count.return_value = 10
    repository.subscriptions.return_value = {
        "active": 7,
        "upcoming": 0,
        "expired": 0,
        "expiring_soon": 2,
        "unpaid": 1,
        "items": [],
    }
    repository.active_students_count.return_value = 9
    service = ReportService(repository)

    report = await service.get_dashboard(
        AsyncMock(),
        date(2026, 7, 1),
        date(2026, 7, 31),
        1,
        7,
    )

    assert report.branch_id == 1
    assert report.revenue == 10000
    assert report.active_students == 9
    assert report.active_subscriptions == 7
    assert report.average_attendance_percent == 80.0
    assert report.average_group_occupancy_percent == 50.0
    assert report.expiring_subscriptions == 2
    assert report.unpaid_subscriptions == 1
    assert report.cancelled_lessons == 1
