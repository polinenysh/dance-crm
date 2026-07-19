from datetime import date

from pydantic import BaseModel, Field


class ReportPeriod(BaseModel):
    """Период формирования отчёта."""

    date_from: date
    date_to: date


class DashboardReport(BaseModel):
    """Сводная статистика по сети или филиалу."""

    period: ReportPeriod
    branch_id: int | None
    revenue: int
    active_students: int
    active_subscriptions: int
    average_attendance_percent: float
    average_group_occupancy_percent: float
    expiring_subscriptions: int
    unpaid_subscriptions: int
    cancelled_lessons: int


class BranchRevenueItem(BaseModel):
    """Выручка отдельного филиала."""

    branch_id: int
    branch_name: str
    revenue: int
    payments_count: int


class DailyRevenueItem(BaseModel):
    """Выручка за день."""

    date: date
    revenue: int
    payments_count: int


class RevenueReport(BaseModel):
    """Подробный отчёт по выручке."""

    period: ReportPeriod
    total: int
    payments_count: int
    branches: list[BranchRevenueItem]
    daily: list[DailyRevenueItem]


class GroupAttendanceItem(BaseModel):
    """Посещаемость отдельной группы."""

    group_id: int
    group_name: str
    completed_lessons: int
    expected_visits: int
    actual_visits: int
    average_attendance_percent: float


class AttendanceReport(BaseModel):
    """Отчёт по посещаемости занятий."""

    period: ReportPeriod
    completed_lessons: int
    cancelled_lessons: int
    expected_visits: int
    actual_visits: int
    average_attendance_percent: float
    groups: list[GroupAttendanceItem]


class SubscriptionReportItem(BaseModel):
    """Абонемент, требующий внимания."""

    subscription_id: int
    student_id: int
    student_name: str
    branch_id: int
    branch_name: str
    plan_id: int
    plan_name: str
    starts_on: date
    expires_on: date
    lessons_count: int
    lessons_used: int
    lessons_remaining: int
    days_until_expiration: int
    is_paid: bool


class SubscriptionReport(BaseModel):
    """Сводка по абонементам."""

    active: int
    upcoming: int
    expired: int
    expiring_soon: int
    unpaid: int
    items: list[SubscriptionReportItem]


class GroupReportItem(BaseModel):
    """Заполненность отдельной группы."""

    group_id: int
    group_name: str
    branch_id: int
    branch_name: str
    teacher_id: int
    teacher_name: str
    students_count: int
    capacity: int = Field(gt=0)
    available_places: int
    occupancy_percent: float
    is_active: bool


class GroupsReport(BaseModel):
    """Отчёт по заполненности групп."""

    groups_count: int
    active_groups_count: int
    unique_students_count: int
    average_occupancy_percent: float
    groups: list[GroupReportItem]
