from datetime import date
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.modules.branches.model import Branch
from app.modules.reports.router import report_service
from app.modules.reports.schemas import (
    AttendanceReport,
    DashboardReport,
    GroupsReport,
    ReportPeriod,
    RevenueReport,
    SubscriptionReport,
)


@pytest.mark.asyncio
async def test_reports_require_authorization(client: AsyncClient) -> None:
    response = await client.get("/api/v1/reports/dashboard")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_can_get_dashboard(
    client: AsyncClient,
    owner_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocked = AsyncMock(
        return_value=DashboardReport(
            period=ReportPeriod(
                date_from=date(2026, 7, 1),
                date_to=date(2026, 7, 31),
            ),
            branch_id=None,
            revenue=10000,
            active_students=12,
            active_subscriptions=10,
            average_attendance_percent=80.0,
            average_group_occupancy_percent=60.0,
            expiring_subscriptions=2,
            unpaid_subscriptions=1,
            cancelled_lessons=3,
        )
    )
    monkeypatch.setattr(report_service, "get_dashboard", mocked)

    response = await client.get(
        "/api/v1/reports/dashboard",
        headers=owner_headers,
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )

    assert response.status_code == 200
    assert response.json()["revenue"] == 10000
    assert mocked.await_args.args[3] is None


@pytest.mark.asyncio
async def test_branch_admin_is_automatically_limited_to_own_branch(
    client: AsyncClient,
    branch: Branch,
    branch_admin_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocked = AsyncMock(
        return_value=GroupsReport(
            groups_count=0,
            active_groups_count=0,
            unique_students_count=0,
            average_occupancy_percent=0,
            groups=[],
        )
    )
    monkeypatch.setattr(report_service, "get_groups", mocked)

    response = await client.get(
        "/api/v1/reports/groups",
        headers=branch_admin_headers,
    )

    assert response.status_code == 200
    assert mocked.await_args.args[1] == branch.id


@pytest.mark.asyncio
async def test_branch_admin_cannot_request_another_branch(
    client: AsyncClient,
    second_branch: Branch,
    branch_admin_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/reports/revenue",
        headers=branch_admin_headers,
        params={"branch_id": second_branch.id},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_revenue_endpoint(
    client: AsyncClient,
    owner_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mocked = AsyncMock(
        return_value=RevenueReport(
            period=ReportPeriod(
                date_from=date(2026, 7, 1),
                date_to=date(2026, 7, 31),
            ),
            total=0,
            payments_count=0,
            branches=[],
            daily=[],
        )
    )
    monkeypatch.setattr(report_service, "get_revenue", mocked)

    response = await client.get(
        "/api/v1/reports/revenue",
        headers=owner_headers,
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_attendance_endpoint(
    client: AsyncClient,
    owner_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        report_service,
        "get_attendance",
        AsyncMock(
            return_value=AttendanceReport(
                period=ReportPeriod(
                    date_from=date(2026, 7, 1),
                    date_to=date(2026, 7, 31),
                ),
                completed_lessons=0,
                cancelled_lessons=0,
                expected_visits=0,
                actual_visits=0,
                average_attendance_percent=0,
                groups=[],
            )
        ),
    )

    response = await client.get(
        "/api/v1/reports/attendance",
        headers=owner_headers,
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_subscriptions_endpoint(
    client: AsyncClient,
    owner_headers: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        report_service,
        "get_subscriptions",
        AsyncMock(
            return_value=SubscriptionReport(
                active=0,
                upcoming=0,
                expired=0,
                expiring_soon=0,
                unpaid=0,
                items=[],
            )
        ),
    )

    response = await client.get(
        "/api/v1/reports/subscriptions",
        headers=owner_headers,
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_invalid_period_returns_422(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/reports/revenue",
        headers=owner_headers,
        params={"date_from": "2026-08-01", "date_to": "2026-07-01"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_invalid_query_parameters_return_422(
    client: AsyncClient,
    owner_headers: dict[str, str],
) -> None:
    response = await client.get(
        "/api/v1/reports/subscriptions",
        headers=owner_headers,
        params={"expiring_within_days": 0},
    )

    assert response.status_code == 422
