from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.groups.model import Group, GroupMembership
from app.modules.students.model import Student


class GroupRepository:
    """Репозиторий для работы с учебными группами."""

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
        teacher_id: int | None = None,
        dance_style_id: int | None = None,
        active_only: bool = False,
        search: str | None = None,
    ) -> list[Group]:
        """Возвращает группы с фильтрацией и связанными данными."""

        query: Select[tuple[Group]] = (
            select(Group)
            .options(
                selectinload(Group.branch),
                selectinload(Group.dance_style),
                selectinload(Group.teacher),
                selectinload(Group.memberships).selectinload(
                    GroupMembership.student,
                ),
            )
            .execution_options(
                populate_existing=True,
            )
        )

        if branch_id is not None:
            query = query.where(
                Group.branch_id == branch_id,
            )

        if teacher_id is not None:
            query = query.where(
                Group.teacher_id == teacher_id,
            )

        if dance_style_id is not None:
            query = query.where(
                Group.dance_style_id == dance_style_id,
            )

        if active_only:
            query = query.where(
                Group.is_active.is_(True),
            )

        if search:
            search_value = f"%{search.strip()}%"

            query = query.where(
                Group.name.ilike(search_value),
            )

        query = query.order_by(
            Group.name,
        )

        result = await session.scalars(query)

        return list(result.unique().all())

    async def get_by_id(
        self,
        session: AsyncSession,
        group_id: int,
    ) -> Group | None:
        """Возвращает группу по идентификатору со связанными данными."""

        result = await session.scalars(
            select(Group)
            .options(
                selectinload(Group.branch),
                selectinload(Group.dance_style),
                selectinload(Group.teacher),
                selectinload(Group.memberships).selectinload(
                    GroupMembership.student,
                ),
            )
            .where(
                Group.id == group_id,
            )
            .execution_options(
                populate_existing=True,
            )
        )

        return result.first()

    async def get_by_name_and_branch(
        self,
        session: AsyncSession,
        name: str,
        branch_id: int,
    ) -> Group | None:
        """Возвращает группу по названию внутри филиала."""

        result = await session.scalars(
            select(Group).where(
                Group.branch_id == branch_id,
                Group.name.ilike(name.strip()),
            )
        )

        return result.first()

    async def get_membership(
        self,
        session: AsyncSession,
        group_id: int,
        student_id: int,
    ) -> GroupMembership | None:
        """Возвращает членство ученика в группе."""

        result = await session.scalars(
            select(GroupMembership)
            .options(
                selectinload(GroupMembership.student),
            )
            .where(
                GroupMembership.group_id == group_id,
                GroupMembership.student_id == student_id,
            )
        )

        return result.first()

    async def count_active_students(
        self,
        session: AsyncSession,
        group_id: int,
    ) -> int:
        """Возвращает количество активных учеников в группе."""

        count = await session.scalar(
            select(
                func.count(GroupMembership.id),
            ).where(
                GroupMembership.group_id == group_id,
                GroupMembership.is_active.is_(True),
            )
        )

        return count or 0

    async def get_student_groups(
        self,
        session: AsyncSession,
        student_id: int,
        active_only: bool = True,
    ) -> list[Group]:
        """Возвращает группы, в которых состоит ученик."""

        query: Select[tuple[Group]] = (
            select(Group)
            .join(
                GroupMembership,
                GroupMembership.group_id == Group.id,
            )
            .options(
                selectinload(Group.branch),
                selectinload(Group.dance_style),
                selectinload(Group.teacher),
                selectinload(Group.memberships).selectinload(
                    GroupMembership.student,
                ),
            )
            .where(
                GroupMembership.student_id == student_id,
            )
        )

        if active_only:
            query = query.where(
                GroupMembership.is_active.is_(True),
            )

        query = query.order_by(
            Group.name,
        )

        result = await session.scalars(query)

        return list(result.unique().all())

    async def get_group_students(
        self,
        session: AsyncSession,
        group_id: int,
        active_only: bool = True,
    ) -> list[Student]:
        """Возвращает учеников группы."""

        query: Select[tuple[Student]] = (
            select(Student)
            .join(
                GroupMembership,
                GroupMembership.student_id == Student.id,
            )
            .where(
                GroupMembership.group_id == group_id,
            )
        )

        if active_only:
            query = query.where(
                GroupMembership.is_active.is_(True),
            )

        query = query.order_by(
            Student.last_name,
            Student.first_name,
        )

        result = await session.scalars(query)

        return list(result.all())
    
    async def get_active_student_ids(
        self,
        session: AsyncSession,
        group_id: int,
    ) -> list[int]:
        """Возвращает идентификаторы активных участников группы."""

        result = await session.scalars(
            select(GroupMembership.student_id).where(
                GroupMembership.group_id == group_id,
                GroupMembership.is_active.is_(True),
            )
        )

        return list(result.all())


group_repository = GroupRepository()