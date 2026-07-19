from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Date, and_, case, cast, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.model import Attendance
from app.modules.branches.model import Branch
from app.modules.groups.model import Group, GroupMembership
from app.modules.payments.enums import PaymentStatus
from app.modules.payments.model import Payment
from app.modules.schedule.model import Lesson
from app.modules.students.model import Student
from app.modules.subscription_plans.model import SubscriptionPlan
from app.modules.subscriptions.model import StudentSubscription
from app.modules.teachers.model import Teacher
from app.shared.enums import LessonStatus, StudentStatus

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")


def _datetime_bounds(date_from: date, date_to: date) -> tuple[datetime, datetime]:
    """Преобразует включительный диапазон дат в полуинтервал UTC."""

    local_start = datetime.combine(date_from, time.min, tzinfo=MOSCOW_TIMEZONE)
    local_end = datetime.combine(
        date_to + timedelta(days=1),
        time.min,
        tzinfo=MOSCOW_TIMEZONE,
    )
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


class ReportRepository:
    """Выполняет агрегирующие запросы для отчётов."""

    async def revenue(
        self,
        session: AsyncSession,
        date_from: date,
        date_to: date,
        branch_id: int | None,
    ) -> dict:
        start_at, end_at = _datetime_bounds(date_from, date_to)
        filters = [
            Payment.status == PaymentStatus.COMPLETED,
            Payment.paid_at >= start_at,
            Payment.paid_at < end_at,
        ]
        if branch_id is not None:
            filters.append(Payment.branch_id == branch_id)

        branch_stmt = (
            select(
                Branch.id,
                Branch.name,
                func.coalesce(func.sum(Payment.amount), 0),
                func.count(Payment.id),
            )
            .join(Payment, Payment.branch_id == Branch.id)
            .where(*filters)
            .group_by(Branch.id, Branch.name)
            .order_by(Branch.name)
        )
        branch_rows = (await session.execute(branch_stmt)).all()

        paid_date = cast(func.timezone("Europe/Moscow", Payment.paid_at), Date)
        daily_stmt = (
            select(
                paid_date.label("paid_date"),
                func.coalesce(func.sum(Payment.amount), 0),
                func.count(Payment.id),
            )
            .where(*filters)
            .group_by(paid_date)
            .order_by(paid_date)
        )
        daily_rows = (await session.execute(daily_stmt)).all()

        total = sum(int(row[2]) for row in branch_rows)
        count = sum(int(row[3]) for row in branch_rows)
        return {
            "total": total,
            "payments_count": count,
            "branches": branch_rows,
            "daily": daily_rows,
        }

    async def groups(
        self,
        session: AsyncSession,
        branch_id: int | None,
    ) -> list:
        students_count = func.count(
            distinct(
                case(
                    (GroupMembership.is_active.is_(True), GroupMembership.student_id),
                    else_=None,
                )
            )
        )
        stmt = (
            select(
                Group.id,
                Group.name,
                Branch.id,
                Branch.name,
                Teacher.id,
                Teacher.first_name,
                Teacher.last_name,
                Group.max_students,
                Group.is_active,
                students_count.label("students_count"),
            )
            .join(Branch, Branch.id == Group.branch_id)
            .join(Teacher, Teacher.id == Group.teacher_id)
            .outerjoin(GroupMembership, GroupMembership.group_id == Group.id)
            .group_by(
                Group.id,
                Group.name,
                Branch.id,
                Branch.name,
                Teacher.id,
                Teacher.first_name,
                Teacher.last_name,
                Group.max_students,
                Group.is_active,
            )
            .order_by(Branch.name, Group.name)
        )
        if branch_id is not None:
            stmt = stmt.where(Group.branch_id == branch_id)
        return (await session.execute(stmt)).all()

    async def attendance(
        self,
        session: AsyncSession,
        date_from: date,
        date_to: date,
        branch_id: int | None,
    ) -> dict:
        start_at, end_at = _datetime_bounds(date_from, date_to)
        lesson_filters = [Lesson.starts_at >= start_at, Lesson.starts_at < end_at]
        if branch_id is not None:
            lesson_filters.append(Group.branch_id == branch_id)

        completed_count_stmt = (
            select(func.count(Lesson.id))
            .join(Group, Group.id == Lesson.group_id)
            .where(*lesson_filters, Lesson.status == LessonStatus.COMPLETED)
        )
        cancelled_count_stmt = (
            select(func.count(Lesson.id))
            .join(Group, Group.id == Lesson.group_id)
            .where(*lesson_filters, Lesson.status == LessonStatus.CANCELLED)
        )
        completed_lessons = int((await session.execute(completed_count_stmt)).scalar_one())
        cancelled_lessons = int((await session.execute(cancelled_count_stmt)).scalar_one())

        expected_subquery = (
            select(
                Lesson.id.label("lesson_id"),
                Lesson.group_id.label("group_id"),
                func.count(GroupMembership.id).label("expected_visits"),
            )
            .join(Group, Group.id == Lesson.group_id)
            .outerjoin(
                GroupMembership,
                and_(
                    GroupMembership.group_id == Lesson.group_id,
                    GroupMembership.joined_at <= Lesson.starts_at,
                    (GroupMembership.left_at.is_(None)) | (GroupMembership.left_at > Lesson.starts_at),
                ),
            )
            .where(*lesson_filters, Lesson.status == LessonStatus.COMPLETED)
            .group_by(Lesson.id, Lesson.group_id)
            .subquery()
        )
        actual_subquery = (
            select(
                Attendance.lesson_id.label("lesson_id"),
                func.count(Attendance.id).label("actual_visits"),
            )
            .group_by(Attendance.lesson_id)
            .subquery()
        )
        group_stmt = (
            select(
                Group.id,
                Group.name,
                func.count(expected_subquery.c.lesson_id),
                func.coalesce(func.sum(expected_subquery.c.expected_visits), 0),
                func.coalesce(func.sum(actual_subquery.c.actual_visits), 0),
            )
            .join(expected_subquery, expected_subquery.c.group_id == Group.id)
            .outerjoin(
                actual_subquery,
                actual_subquery.c.lesson_id == expected_subquery.c.lesson_id,
            )
            .group_by(Group.id, Group.name)
            .order_by(Group.name)
        )
        group_rows = (await session.execute(group_stmt)).all()
        return {
            "completed_lessons": completed_lessons,
            "cancelled_lessons": cancelled_lessons,
            "groups": group_rows,
        }

    async def subscriptions(
        self,
        session: AsyncSession,
        branch_id: int | None,
        expiring_within_days: int,
        include_all: bool,
    ) -> dict:
        today = datetime.now(MOSCOW_TIMEZONE).date()
        expiring_before = today + timedelta(days=expiring_within_days)

        attendance_count = (
            select(
                Attendance.subscription_id,
                func.count(Attendance.id).label("lessons_used"),
            )
            .group_by(Attendance.subscription_id)
            .subquery()
        )
        payment_count = (
            select(
                Payment.subscription_id,
                func.count(Payment.id).label("completed_payments"),
            )
            .where(Payment.status == PaymentStatus.COMPLETED)
            .group_by(Payment.subscription_id)
            .subquery()
        )
        filters = []
        if branch_id is not None:
            filters.append(StudentSubscription.branch_id == branch_id)

        counts_stmt = select(
            func.count(case((StudentSubscription.starts_on > today, 1))),
            func.count(
                case(
                    (
                        and_(
                            StudentSubscription.starts_on <= today,
                            StudentSubscription.expires_on >= today,
                        ),
                        1,
                    )
                )
            ),
            func.count(case((StudentSubscription.expires_on < today, 1))),
            func.count(
                case(
                    (
                        and_(
                            StudentSubscription.expires_on >= today,
                            StudentSubscription.expires_on <= expiring_before,
                        ),
                        1,
                    )
                )
            ),
            func.count(case((func.coalesce(payment_count.c.completed_payments, 0) == 0, 1))),
        ).outerjoin(
            payment_count,
            payment_count.c.subscription_id == StudentSubscription.id,
        )
        if filters:
            counts_stmt = counts_stmt.where(*filters)
        counts = (await session.execute(counts_stmt)).one()

        item_filters = list(filters)
        if not include_all:
            item_filters.append(
                (StudentSubscription.expires_on <= expiring_before)
                | (func.coalesce(payment_count.c.completed_payments, 0) == 0)
            )
        items_stmt = (
            select(
                StudentSubscription.id,
                Student.id,
                Student.first_name,
                Student.last_name,
                Branch.id,
                Branch.name,
                SubscriptionPlan.id,
                SubscriptionPlan.name,
                StudentSubscription.starts_on,
                StudentSubscription.expires_on,
                StudentSubscription.lessons_count,
                func.coalesce(attendance_count.c.lessons_used, 0),
                func.coalesce(payment_count.c.completed_payments, 0),
            )
            .join(Student, Student.id == StudentSubscription.student_id)
            .join(Branch, Branch.id == StudentSubscription.branch_id)
            .join(SubscriptionPlan, SubscriptionPlan.id == StudentSubscription.plan_id)
            .outerjoin(
                attendance_count,
                attendance_count.c.subscription_id == StudentSubscription.id,
            )
            .outerjoin(
                payment_count,
                payment_count.c.subscription_id == StudentSubscription.id,
            )
            .where(*item_filters)
            .order_by(StudentSubscription.expires_on, Student.last_name)
        )
        items = (await session.execute(items_stmt)).all()
        return {
            "upcoming": int(counts[0]),
            "active": int(counts[1]),
            "expired": int(counts[2]),
            "expiring_soon": int(counts[3]),
            "unpaid": int(counts[4]),
            "items": items,
        }

    async def group_students_count(
        self,
        session: AsyncSession,
        branch_id: int | None,
    ) -> int:
        """Считает уникальных учеников в активных составах групп."""

        stmt = (
            select(func.count(distinct(GroupMembership.student_id)))
            .join(Group, Group.id == GroupMembership.group_id)
            .where(GroupMembership.is_active.is_(True))
        )
        if branch_id is not None:
            stmt = stmt.where(Group.branch_id == branch_id)
        return int((await session.execute(stmt)).scalar_one())

    async def active_students_count(
        self,
        session: AsyncSession,
        branch_id: int | None,
    ) -> int:
        stmt = (
            select(func.count(distinct(Student.id)))
            .join(GroupMembership, GroupMembership.student_id == Student.id)
            .join(Group, Group.id == GroupMembership.group_id)
            .where(
                Student.status == StudentStatus.ACTIVE,
                GroupMembership.is_active.is_(True),
                Group.is_active.is_(True),
            )
        )
        if branch_id is not None:
            stmt = stmt.where(Student.branch_id == branch_id)
        return int((await session.execute(stmt)).scalar_one())


report_repository = ReportRepository()
