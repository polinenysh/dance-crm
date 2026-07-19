from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.attendance.model import Attendance
from app.modules.attendance.repository import attendance_repository
from app.modules.attendance.schemas import AttendanceSyncRequest, LessonAttendanceResponse
from app.modules.auth.dependencies import ensure_branch_access
from app.modules.groups.repository import group_repository
from app.modules.schedule.repository import schedule_repository
from app.modules.students.repository import student_repository
from app.modules.users.model import User
from app.shared.enums import LessonStatus

MOSCOW_TIMEZONE = ZoneInfo("Europe/Moscow")
EDIT_WINDOW = timedelta(hours=2)


class AttendanceService:
    """Сервис синхронизации посещаемости."""

    async def get_lesson(self, session: AsyncSession, lesson_id: int, current_user: User):
        """Возвращает занятие с проверкой доступа."""
        lesson = await schedule_repository.get_lesson_by_id(session, lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="Занятие не найдено")
        ensure_branch_access(current_user, lesson.group.branch_id)
        return lesson

    async def get_lesson_attendance(self, session: AsyncSession, lesson_id: int,
                                    current_user: User) -> LessonAttendanceResponse:
        """Возвращает текущий список присутствующих."""
        await self.get_lesson(session, lesson_id, current_user)
        items = await attendance_repository.get_by_lesson(session, lesson_id)
        return LessonAttendanceResponse(lesson_id=lesson_id, students_count=len(items), attendances=items)

    def validate_edit_time(self, lesson) -> None:
        """Проверяет статус, окончание занятия и двухчасовое окно исправлений."""
        now = datetime.now(UTC)
        if lesson.status == LessonStatus.CANCELLED:
            raise HTTPException(status_code=409, detail="Нельзя изменить посещаемость отменённого занятия")
        if lesson.status == LessonStatus.PLANNED and now < lesson.ends_at:
            raise HTTPException(status_code=409, detail="Нельзя завершить будущее или ещё не закончившееся занятие")
        if lesson.status == LessonStatus.COMPLETED:
            if lesson.completed_at is None:
                raise HTTPException(status_code=409, detail="У занятия отсутствует время завершения")
            if now > lesson.completed_at + EDIT_WINDOW:
                raise HTTPException(status_code=409, detail="Посещаемость можно исправлять только в течение 2 часов после завершения")

    async def validate_student(self, session: AsyncSession, lesson, student_id: int):
        """Проверяет ученика и его активное членство в группе."""
        student = await student_repository.get_by_id(session, student_id)
        if student is None:
            raise HTTPException(status_code=404, detail=f"Ученик {student_id} не найден")
        if student.branch_id != lesson.group.branch_id:
            raise HTTPException(status_code=409, detail=f"Ученик {student_id} относится к другому филиалу")
        membership = await group_repository.get_membership(session, lesson.group_id, student.id)
        if membership is None or not membership.is_active:
            raise HTTPException(status_code=409, detail=f"Ученик {student_id} не является активным участником группы")
        return student

    async def sync_attendance(self, session: AsyncSession, lesson_id: int,
                              data: AttendanceSyncRequest, current_user: User) -> LessonAttendanceResponse:
        """Синхронизирует полный список и при первом сохранении завершает занятие."""
        lesson = await self.get_lesson(session, lesson_id, current_user)
        self.validate_edit_time(lesson)

        existing = await attendance_repository.get_by_lesson(session, lesson.id)
        existing_by_student = {item.student_id: item for item in existing}
        requested_ids = set(data.student_ids)
        existing_ids = set(existing_by_student)
        to_add = requested_ids - existing_ids
        to_remove = existing_ids - requested_ids
        lesson_date = lesson.starts_at.astimezone(MOSCOW_TIMEZONE).date()
        new_items: list[Attendance] = []

        for student_id in sorted(to_add):
            student = await self.validate_student(session, lesson, student_id)
            subscription = await attendance_repository.get_valid_subscription(
                session, student.id, lesson.group.branch_id, lesson_date
            )
            if subscription is None:
                raise HTTPException(
                    status_code=409,
                    detail=f"У ученика {student.first_name} {student.last_name} нет действующего абонемента со свободными занятиями",
                )
            new_items.append(Attendance(
                lesson_id=lesson.id,
                student_id=student.id,
                subscription_id=subscription.id,
                marked_by=current_user.id,
            ))

        for student_id in to_remove:
            await session.delete(existing_by_student[student_id])
        session.add_all(new_items)

        if lesson.status == LessonStatus.PLANNED:
            lesson.status = LessonStatus.COMPLETED
            lesson.completed_at = datetime.now(UTC)

        await session.commit()
        items = await attendance_repository.get_by_lesson(session, lesson.id)
        return LessonAttendanceResponse(lesson_id=lesson.id, students_count=len(items), attendances=items)


attendance_service = AttendanceService()