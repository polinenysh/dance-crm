from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.teachers.model import Teacher
from app.modules.teachers.schemas import TeacherCreate, TeacherUpdate
from app.shared.repository import BaseRepository


class TeacherRepository(BaseRepository[Teacher, TeacherCreate, TeacherUpdate]):
    """Репозиторий для работы с преподавателями."""

    def __init__(self) -> None:
        """Инициализирует репозиторий преподавателей."""

        super().__init__(Teacher)

    async def get_all(
        self,
        session: AsyncSession,
        dance_style_id: int | None = None,
        active_only: bool = False,
        search: str | None = None,
    ) -> list[Teacher]:
        """Возвращает преподавателей с фильтрацией."""

        query: Select[tuple[Teacher]] = select(Teacher).options(
            selectinload(Teacher.dance_styles),
        )

        if dance_style_id is not None:
            query = query.where(Teacher.dance_styles.any(id=dance_style_id))
        if active_only:
            query = query.where(Teacher.is_active.is_(True))
        if search:
            value = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Teacher.first_name.ilike(value),
                    Teacher.last_name.ilike(value),
                    Teacher.phone.ilike(value),
                    Teacher.email.ilike(value),
                )
            )

        result = await session.scalars(query.order_by(Teacher.last_name, Teacher.first_name))
        return list(result.unique().all())

    async def get_by_id(
        self,
        session: AsyncSession,
        object_id: int,
    ) -> Teacher | None:
        """Возвращает преподавателя со связанными направлениями."""

        result = await session.scalars(
            select(Teacher).options(selectinload(Teacher.dance_styles)).where(Teacher.id == object_id)
        )
        return result.first()


teacher_repository = TeacherRepository()
