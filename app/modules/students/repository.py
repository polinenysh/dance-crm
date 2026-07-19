from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.students.model import Student
from app.modules.students.schemas import StudentCreate, StudentUpdate
from app.shared.enums import StudentStatus
from app.shared.repository import BaseRepository


class StudentRepository(
    BaseRepository[
        Student,
        StudentCreate,
        StudentUpdate,
    ]
):
    """Репозиторий для работы с учениками."""

    def __init__(self) -> None:
        """Инициализирует репозиторий учеников."""

        super().__init__(Student)

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
        parent_id: int | None = None,
        status: StudentStatus | None = None,
        search: str | None = None,
    ) -> list[Student]:
        """Возвращает учеников со связанными данными."""

        query: Select[tuple[Student]] = (
            select(Student)
            .options(
                selectinload(Student.parent),
                selectinload(Student.branch),
            )
        )

        if branch_id is not None:
            query = query.where(
                Student.branch_id == branch_id
            )

        if parent_id is not None:
            query = query.where(
                Student.parent_id == parent_id
            )

        if status is not None:
            query = query.where(
                Student.status == status
            )

        if search:
            search_value = f"%{search.strip()}%"

            query = query.where(
                or_(
                    Student.first_name.ilike(search_value),
                    Student.last_name.ilike(search_value),
                )
            )

        query = query.order_by(
            Student.last_name,
            Student.first_name,
        )

        result = await session.scalars(query)
        return list(result.all())

    async def get_by_id(
        self,
        session: AsyncSession,
        object_id: int,
    ) -> Student | None:
        """Возвращает ученика со связанными данными."""

        result = await session.scalars(
            select(Student)
            .options(
                selectinload(Student.parent),
                selectinload(Student.branch),
            )
            .where(Student.id == object_id)
        )

        return result.first()


student_repository = StudentRepository()