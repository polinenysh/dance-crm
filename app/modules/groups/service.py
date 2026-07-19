from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import ensure_branch_access
from app.modules.branches.repository import branch_repository
from app.modules.dance_styles.repository import dance_style_repository
from app.modules.groups.model import Group, GroupMembership
from app.modules.groups.repository import group_repository
from app.modules.groups.schemas import (
    GroupCreate,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdate,
)
from app.modules.students.repository import student_repository
from app.modules.teachers.repository import teacher_repository
from app.modules.users.model import User
from app.shared.enums import StudentStatus, UserRole


class GroupService:
    """Сервис бизнес-логики учебных групп."""

    async def get_all(
        self,
        session: AsyncSession,
        current_user: User,
        branch_id: int | None = None,
        teacher_id: int | None = None,
        dance_style_id: int | None = None,
        active_only: bool = False,
        search: str | None = None,
    ) -> list[GroupResponse]:
        """Возвращает доступные сотруднику группы."""

        if current_user.role == UserRole.BRANCH_ADMIN:
            branch_id = current_user.branch_id

        groups = await group_repository.get_all(
            session=session,
            branch_id=branch_id,
            teacher_id=teacher_id,
            dance_style_id=dance_style_id,
            active_only=active_only,
            search=search,
        )

        return [
            self.build_response(group)
            for group in groups
        ]

    async def get_group(
        self,
        session: AsyncSession,
        group_id: int,
        current_user: User,
    ) -> Group:
        """Возвращает группу с проверкой доступа."""

        group = await group_repository.get_by_id(
            session,
            group_id,
        )

        if group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Группа не найдена",
            )

        ensure_branch_access(
            current_user,
            group.branch_id,
        )

        return group

    async def get_by_id(
        self,
        session: AsyncSession,
        group_id: int,
        current_user: User,
    ) -> GroupResponse:
        """Возвращает группу по идентификатору."""

        group = await self.get_group(
            session,
            group_id,
            current_user,
        )

        return self.build_response(group)

    async def validate_relations(
        self,
        session: AsyncSession,
        branch_id: int,
        dance_style_id: int,
        teacher_id: int,
    ) -> None:
        """Проверяет филиал, направление и преподавателя."""

        branch = await branch_repository.get_by_id(
            session,
            branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Филиал не найден",
            )

        if not branch.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя использовать неактивный филиал",
            )

        dance_style = await dance_style_repository.get_by_id(
            session,
            dance_style_id,
        )

        if dance_style is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Направление не найдено",
            )

        if not dance_style.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя использовать неактивное направление",
            )

        teacher = await teacher_repository.get_by_id(
            session,
            teacher_id,
        )

        if teacher is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Преподаватель не найден",
            )

        if not teacher.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя назначить неактивного преподавателя",
            )

        teacher_style_ids = {
            style.id
            for style in teacher.dance_styles
        }

        if dance_style_id not in teacher_style_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Преподаватель не ведёт выбранное направление",
            )

    async def create(
        self,
        session: AsyncSession,
        data: GroupCreate,
        current_user: User,
    ) -> GroupResponse:
        """Создаёт учебную группу."""

        ensure_branch_access(
            current_user,
            data.branch_id,
        )

        await self.validate_relations(
            session=session,
            branch_id=data.branch_id,
            dance_style_id=data.dance_style_id,
            teacher_id=data.teacher_id,
        )

        existing_group = (
            await group_repository.get_by_name_and_branch(
                session,
                data.name,
                data.branch_id,
            )
        )

        if existing_group is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Группа с таким названием уже существует в филиале",
            )

        group = Group(
            **data.model_dump(),
            is_active=True,
        )

        session.add(group)
        await session.commit()

        created_group = await group_repository.get_by_id(
            session,
            group.id,
        )

        if created_group is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить созданную группу",
            )

        return self.build_response(created_group)

    async def update(
        self,
        session: AsyncSession,
        group_id: int,
        data: GroupUpdate,
        current_user: User,
    ) -> GroupResponse:
        """Обновляет учебную группу."""

        group = await self.get_group(
            session,
            group_id,
            current_user,
        )

        target_branch_id = (
            data.branch_id
            if data.branch_id is not None
            else group.branch_id
        )
        target_dance_style_id = (
            data.dance_style_id
            if data.dance_style_id is not None
            else group.dance_style_id
        )
        target_teacher_id = (
            data.teacher_id
            if data.teacher_id is not None
            else group.teacher_id
        )

        ensure_branch_access(
            current_user,
            target_branch_id,
        )

        await self.validate_relations(
            session=session,
            branch_id=target_branch_id,
            dance_style_id=target_dance_style_id,
            teacher_id=target_teacher_id,
        )

        if data.name is not None:
            existing_group = (
                await group_repository.get_by_name_and_branch(
                    session,
                    data.name,
                    target_branch_id,
                )
            )

            if (
                existing_group is not None
                and existing_group.id != group.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Группа с таким названием уже существует "
                        "в филиале"
                    ),
                )

        active_students_count = sum(
            1
            for membership in group.memberships
            if membership.is_active
        )

        if (
            data.max_students is not None
            and data.max_students < active_students_count
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Максимальное количество учеников не может быть "
                    "меньше текущего состава группы"
                ),
            )

        update_data = data.model_dump(
            exclude_unset=True,
        )

        for field, value in update_data.items():
            setattr(group, field, value)

        await session.commit()

        updated_group = await group_repository.get_by_id(
            session,
            group.id,
        )

        if updated_group is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновлённую группу",
            )

        return self.build_response(updated_group)

    async def add_student(
        self,
        session: AsyncSession,
        group_id: int,
        student_id: int,
        current_user: User,
    ) -> GroupResponse:
        """Добавляет ученика в группу."""

        group = await self.get_group(
            session,
            group_id,
            current_user,
        )

        if not group.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя добавить ученика в неактивную группу",
            )

        student = await student_repository.get_by_id(
            session,
            student_id,
        )

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ученик не найден",
            )

        if student.status != StudentStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="В группу можно добавить только активного ученика",
            )

        if student.branch_id != group.branch_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ученик и группа относятся к разным филиалам",
            )

        membership = await group_repository.get_membership(
            session,
            group.id,
            student.id,
        )

        if membership is not None and membership.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ученик уже состоит в этой группе",
            )

        students_count = await group_repository.count_active_students(
            session,
            group.id,
        )

        if students_count >= group.max_students:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="В группе достигнуто максимальное число учеников",
            )

        if membership is None:
            membership = GroupMembership(
                group_id=group.id,
                student_id=student.id,
                is_active=True,
                left_at=None,
            )

            session.add(membership)
        else:
            membership.is_active = True
            membership.joined_at = datetime.now(UTC)
            membership.left_at = None

        await session.commit()

        updated_group = await group_repository.get_by_id(
            session,
            group.id,
        )

        if updated_group is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновлённую группу",
            )

        return self.build_response(updated_group)

    async def remove_student(
        self,
        session: AsyncSession,
        group_id: int,
        student_id: int,
        current_user: User,
    ) -> GroupResponse:
        """Исключает ученика из группы."""

        group = await self.get_group(
            session,
            group_id,
            current_user,
        )

        membership = await group_repository.get_membership(
            session,
            group.id,
            student_id,
        )

        if membership is None or not membership.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ученик не состоит в этой группе",
            )

        membership.is_active = False
        membership.left_at = datetime.now(UTC)

        await session.commit()

        updated_group = await group_repository.get_by_id(
            session,
            group.id,
        )

        if updated_group is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновлённую группу",
            )

        return self.build_response(updated_group)

    def build_response(
        self,
        group: Group,
    ) -> GroupResponse:
        """Формирует API-ответ с активным составом группы."""

        active_memberships = [
            membership
            for membership in group.memberships
            if membership.is_active
        ]

        active_memberships.sort(
            key=lambda membership: (
                membership.student.last_name,
                membership.student.first_name,
            )
        )

        return GroupResponse(
            id=group.id,
            name=group.name,
            max_students=group.max_students,
            students_count=len(active_memberships),
            is_active=group.is_active,
            branch=group.branch,
            dance_style=group.dance_style,
            teacher=group.teacher,
            students=[
                GroupMemberResponse(
                    membership_id=membership.id,
                    student=membership.student,
                    joined_at=membership.joined_at,
                )
                for membership in active_memberships
            ],
            created_at=group.created_at,
            updated_at=group.updated_at,
        )


group_service = GroupService()