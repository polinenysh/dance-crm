from datetime import date

from fastapi import APIRouter, Query

from app.core.logging import audit_event
from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep
from app.modules.reports.dependencies import resolve_branch_id, validate_period
from app.modules.reports.schemas import (
    AttendanceReport,
    DashboardReport,
    GroupsReport,
    RevenueReport,
    SubscriptionReport,
)
from app.modules.reports.service import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


def _month_start(today: date) -> date:
    return today.replace(day=1)


@router.get("/dashboard", response_model=DashboardReport)
async def get_dashboard(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: int | None = Query(default=None, gt=0),
    expiring_within_days: int = Query(default=7, ge=1, le=90),
) -> DashboardReport:
    """Возвращает основную сводку по сети или филиалу."""

    today = date.today()
    resolved_from = date_from or _month_start(today)
    resolved_to = date_to or today
    validate_period(resolved_from, resolved_to)
    resolved_branch = resolve_branch_id(current_user, branch_id)
    result = await report_service.get_dashboard(
        session, resolved_from, resolved_to, resolved_branch, expiring_within_days
    )
    audit_event(
        "report.dashboard_generated",
        actor_id=current_user.id,
        entity="report",
        branch_id=resolved_branch,
        details={"date_from": resolved_from, "date_to": resolved_to},
    )
    return result


@router.get("/revenue", response_model=RevenueReport)
async def get_revenue(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: int | None = Query(default=None, gt=0),
) -> RevenueReport:
    """Возвращает выручку по филиалам и дням."""

    today = date.today()
    resolved_from = date_from or _month_start(today)
    resolved_to = date_to or today
    validate_period(resolved_from, resolved_to)
    resolved_branch = resolve_branch_id(current_user, branch_id)
    result = await report_service.get_revenue(session, resolved_from, resolved_to, resolved_branch)
    audit_event(
        "report.revenue_generated",
        actor_id=current_user.id,
        entity="report",
        branch_id=resolved_branch,
        details={"date_from": resolved_from, "date_to": resolved_to},
    )
    return result


@router.get("/attendance", response_model=AttendanceReport)
async def get_attendance(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    date_from: date | None = None,
    date_to: date | None = None,
    branch_id: int | None = Query(default=None, gt=0),
) -> AttendanceReport:
    """Возвращает посещаемость и отменённые занятия."""

    today = date.today()
    resolved_from = date_from or _month_start(today)
    resolved_to = date_to or today
    validate_period(resolved_from, resolved_to)
    resolved_branch = resolve_branch_id(current_user, branch_id)
    result = await report_service.get_attendance(session, resolved_from, resolved_to, resolved_branch)
    audit_event(
        "report.attendance_generated",
        actor_id=current_user.id,
        entity="report",
        branch_id=resolved_branch,
        details={"date_from": resolved_from, "date_to": resolved_to},
    )
    return result


@router.get("/subscriptions", response_model=SubscriptionReport)
async def get_subscriptions(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    branch_id: int | None = Query(default=None, gt=0),
    expiring_within_days: int = Query(default=7, ge=1, le=90),
    include_all: bool = Query(default=False),
) -> SubscriptionReport:
    """Возвращает состояние и проблемные абонементы."""

    resolved_branch = resolve_branch_id(current_user, branch_id)
    result = await report_service.get_subscriptions(session, resolved_branch, expiring_within_days, include_all)
    audit_event(
        "report.subscriptions_generated",
        actor_id=current_user.id,
        entity="report",
        branch_id=resolved_branch,
        details={"expiring_within_days": expiring_within_days, "include_all": include_all},
    )
    return result


@router.get("/groups", response_model=GroupsReport)
async def get_groups(
    session: SessionDep,
    current_user: AdminOrOwnerDep,
    branch_id: int | None = Query(default=None, gt=0),
) -> GroupsReport:
    """Возвращает заполненность учебных групп."""

    resolved_branch = resolve_branch_id(current_user, branch_id)
    result = await report_service.get_groups(session, resolved_branch)
    audit_event("report.groups_generated", actor_id=current_user.id, entity="report", branch_id=resolved_branch)
    return result
