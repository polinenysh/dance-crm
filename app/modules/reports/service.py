from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.repository import ReportRepository, report_repository
from app.modules.reports.schemas import (
    AttendanceReport,
    BranchRevenueItem,
    DailyRevenueItem,
    DashboardReport,
    GroupAttendanceItem,
    GroupReportItem,
    GroupsReport,
    ReportPeriod,
    RevenueReport,
    SubscriptionReport,
    SubscriptionReportItem,
)


def _percent(numerator: int, denominator: int) -> float:
    """Безопасно вычисляет процент с округлением до двух знаков."""

    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


class ReportService:
    """Формирует DTO статистических отчётов."""

    def __init__(self, repository: ReportRepository) -> None:
        self.repository = repository

    async def get_revenue(
        self,
        session: AsyncSession,
        date_from: date,
        date_to: date,
        branch_id: int | None,
    ) -> RevenueReport:
        data = await self.repository.revenue(session, date_from, date_to, branch_id)
        return RevenueReport(
            period=ReportPeriod(date_from=date_from, date_to=date_to),
            total=data["total"],
            payments_count=data["payments_count"],
            branches=[
                BranchRevenueItem(
                    branch_id=row[0],
                    branch_name=row[1],
                    revenue=int(row[2]),
                    payments_count=int(row[3]),
                )
                for row in data["branches"]
            ],
            daily=[
                DailyRevenueItem(
                    date=row[0],
                    revenue=int(row[1]),
                    payments_count=int(row[2]),
                )
                for row in data["daily"]
            ],
        )

    async def get_groups(
        self,
        session: AsyncSession,
        branch_id: int | None,
    ) -> GroupsReport:
        rows = await self.repository.groups(session, branch_id)
        items: list[GroupReportItem] = []
        total_students = 0
        total_capacity = 0

        for row in rows:
            students_count = int(row[9])
            capacity = int(row[7])
            total_students += students_count
            total_capacity += capacity
            items.append(
                GroupReportItem(
                    group_id=row[0],
                    group_name=row[1],
                    branch_id=row[2],
                    branch_name=row[3],
                    teacher_id=row[4],
                    teacher_name=f"{row[5]} {row[6]}",
                    students_count=students_count,
                    capacity=capacity,
                    available_places=max(capacity - students_count, 0),
                    occupancy_percent=_percent(students_count, capacity),
                    is_active=row[8],
                )
            )

        unique_students = await self.repository.group_students_count(session, branch_id)
        return GroupsReport(
            groups_count=len(items),
            active_groups_count=sum(item.is_active for item in items),
            unique_students_count=unique_students,
            average_occupancy_percent=_percent(total_students, total_capacity),
            groups=items,
        )

    async def get_attendance(
        self,
        session: AsyncSession,
        date_from: date,
        date_to: date,
        branch_id: int | None,
    ) -> AttendanceReport:
        data = await self.repository.attendance(session, date_from, date_to, branch_id)
        groups: list[GroupAttendanceItem] = []
        expected_total = 0
        actual_total = 0
        for row in data["groups"]:
            expected = int(row[3])
            actual = int(row[4])
            expected_total += expected
            actual_total += actual
            groups.append(
                GroupAttendanceItem(
                    group_id=row[0],
                    group_name=row[1],
                    completed_lessons=int(row[2]),
                    expected_visits=expected,
                    actual_visits=actual,
                    average_attendance_percent=_percent(actual, expected),
                )
            )
        return AttendanceReport(
            period=ReportPeriod(date_from=date_from, date_to=date_to),
            completed_lessons=data["completed_lessons"],
            cancelled_lessons=data["cancelled_lessons"],
            expected_visits=expected_total,
            actual_visits=actual_total,
            average_attendance_percent=_percent(actual_total, expected_total),
            groups=groups,
        )

    async def get_subscriptions(
        self,
        session: AsyncSession,
        branch_id: int | None,
        expiring_within_days: int,
        include_all: bool,
    ) -> SubscriptionReport:
        data = await self.repository.subscriptions(
            session,
            branch_id,
            expiring_within_days,
            include_all,
        )
        today = date.today()
        items = []
        for row in data["items"]:
            lessons_used = int(row[11])
            lessons_count = int(row[10])
            items.append(
                SubscriptionReportItem(
                    subscription_id=row[0],
                    student_id=row[1],
                    student_name=f"{row[2]} {row[3]}",
                    branch_id=row[4],
                    branch_name=row[5],
                    plan_id=row[6],
                    plan_name=row[7],
                    starts_on=row[8],
                    expires_on=row[9],
                    lessons_count=lessons_count,
                    lessons_used=lessons_used,
                    lessons_remaining=max(lessons_count - lessons_used, 0),
                    days_until_expiration=(row[9] - today).days,
                    is_paid=int(row[12]) > 0,
                )
            )
        return SubscriptionReport(
            active=data["active"],
            upcoming=data["upcoming"],
            expired=data["expired"],
            expiring_soon=data["expiring_soon"],
            unpaid=data["unpaid"],
            items=items,
        )

    async def get_dashboard(
        self,
        session: AsyncSession,
        date_from: date,
        date_to: date,
        branch_id: int | None,
        expiring_within_days: int,
    ) -> DashboardReport:
        revenue = await self.get_revenue(session, date_from, date_to, branch_id)
        attendance = await self.get_attendance(session, date_from, date_to, branch_id)
        groups = await self.get_groups(session, branch_id)
        subscriptions = await self.get_subscriptions(
            session,
            branch_id,
            expiring_within_days,
            include_all=False,
        )
        active_students = await self.repository.active_students_count(session, branch_id)
        return DashboardReport(
            period=ReportPeriod(date_from=date_from, date_to=date_to),
            branch_id=branch_id,
            revenue=revenue.total,
            active_students=active_students,
            active_subscriptions=subscriptions.active,
            average_attendance_percent=attendance.average_attendance_percent,
            average_group_occupancy_percent=(groups.average_occupancy_percent),
            expiring_subscriptions=subscriptions.expiring_soon,
            unpaid_subscriptions=subscriptions.unpaid,
            cancelled_lessons=attendance.cancelled_lessons,
        )


report_service = ReportService(report_repository)
