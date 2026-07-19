from fastapi import APIRouter

from app.db.session import SessionDep
from app.modules.attendance.schemas import AttendanceSyncRequest, LessonAttendanceResponse
from app.modules.attendance.service import attendance_service
from app.modules.auth.dependencies import AdminOrOwnerDep

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.get("/lessons/{lesson_id}", response_model=LessonAttendanceResponse)
async def get_lesson_attendance(
    lesson_id: int,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> LessonAttendanceResponse:
    """Возвращает посещаемость занятия."""
    return await attendance_service.get_lesson_attendance(session, lesson_id, current_user)


@router.put("/lessons/{lesson_id}", response_model=LessonAttendanceResponse)
async def sync_lesson_attendance(
    lesson_id: int,
    data: AttendanceSyncRequest,
    session: SessionDep,
    current_user: AdminOrOwnerDep,
) -> LessonAttendanceResponse:
    """Синхронизирует полный список присутствующих и завершает занятие."""
    return await attendance_service.sync_attendance(session, lesson_id, data, current_user)
