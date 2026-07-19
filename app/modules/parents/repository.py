from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.parents.model import Parent
from app.modules.parents.schemas import ParentCreate, ParentUpdate
from app.modules.students.model import Student
from app.shared.repository import BaseRepository


class ParentRepository(
    BaseRepository[
        Parent,
        ParentCreate,
        ParentUpdate,
    ]
):
    """Репозиторий для работы с родителями."""

    def __init__(self) -> None:
        """Инициализирует репозиторий родителей."""

        super().__init__(Parent)

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
        search: str | None = None,
    ) -> list[Parent]:
        """Возвращает родителей с фильтрацией и поиском."""

        query: Select[tuple[Parent]] = select(Parent)

        if branch_id is not None:
            query = query.join(Student).where(Student.branch_id == branch_id).distinct()

        if search:
            search_value = f"%{search.strip()}%"

            query = query.where(
                or_(
                    Parent.first_name.ilike(search_value),
                    Parent.last_name.ilike(search_value),
                    Parent.phone.ilike(search_value),
                )
            )

        query = query.order_by(
            Parent.last_name,
            Parent.first_name,
        )

        result = await session.scalars(query)

        return list(result.all())

    async def get_by_phone(
        self,
        session: AsyncSession,
        phone: str,
    ) -> Parent | None:
        """Возвращает родителя по номеру телефона."""

        result = await session.scalars(
            select(Parent).where(
                Parent.phone == phone,
            )
        )

        return result.first()

    async def has_student_in_branch(
        self,
        session: AsyncSession,
        parent_id: int,
        branch_id: int,
    ) -> bool:
        """Проверяет наличие ребёнка родителя в филиале."""

        student_id = await session.scalar(
            select(Student.id)
            .where(
                Student.parent_id == parent_id,
                Student.branch_id == branch_id,
            )
            .limit(1)
        )

        return student_id is not None


parent_repository = ParentRepository()
