from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.dependencies import ensure_branch_access
from app.modules.branches.repository import branch_repository
from app.modules.parents.repository import parent_repository
from app.modules.students.model import Student
from app.modules.students.repository import student_repository
from app.modules.students.schemas import StudentCreate, StudentUpdate
from app.modules.users.model import User
from app.shared.enums import StudentStatus, UserRole


class StudentService:
    """Сервис бизнес-логики учеников."""

    async def get_all(
        self,
        session: AsyncSession,
        current_user: User,
        branch_id: int | None = None,
        parent_id: int | None = None,
        student_status: StudentStatus | None = None,
        search: str | None = None,
    ) -> list[Student]:
        """Возвращает доступный сотруднику список учеников."""

        if current_user.role == UserRole.BRANCH_ADMIN:
            branch_id = current_user.branch_id

        return await student_repository.get_all(
            session,
            branch_id=branch_id,
            parent_id=parent_id,
            status=student_status,
            search=search,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        student_id: int,
        current_user: User,
    ) -> Student:
        """Возвращает ученика с проверкой филиала."""

        student = await student_repository.get_by_id(
            session,
            student_id,
        )

        if student is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ученик не найден",
            )

        ensure_branch_access(
            current_user,
            student.branch_id,
        )

        return student

    async def create(
        self,
        session: AsyncSession,
        data: StudentCreate,
        current_user: User,
    ) -> Student:
        """Создаёт карточку ученика."""

        ensure_branch_access(
            current_user,
            data.branch_id,
        )

        branch = await branch_repository.get_by_id(
            session,
            data.branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Филиал не найден",
            )

        if not branch.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя добавить ученика в неактивный филиал",
            )

        parent = await parent_repository.get_by_id(
            session,
            data.parent_id,
        )

        if parent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Родитель не найден",
            )

        student = Student(
            **data.model_dump(),
            status=StudentStatus.ACTIVE,
            created_by=current_user.id,
        )

        session.add(student)
        await session.commit()

        created_student = await student_repository.get_by_id(
            session,
            student.id,
        )

        if created_student is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить созданного ученика",
            )

        return created_student

    async def update(
        self,
        session: AsyncSession,
        student_id: int,
        data: StudentUpdate,
        current_user: User,
    ) -> Student:
        """Обновляет карточку ученика."""

        student = await self.get_by_id(
            session,
            student_id,
            current_user,
        )

        target_branch_id = data.branch_id or student.branch_id
        ensure_branch_access(
            current_user,
            target_branch_id,
        )

        if data.branch_id is not None:
            branch = await branch_repository.get_by_id(
                session,
                data.branch_id,
            )

            if branch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Филиал не найден",
                )

            if not branch.is_active:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Нельзя перевести ученика в неактивный филиал",
                )

        if data.parent_id is not None:
            parent = await parent_repository.get_by_id(
                session,
                data.parent_id,
            )

            if parent is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Родитель не найден",
                )

        await student_repository.update(
            session,
            student,
            data,
        )

        updated_student = await student_repository.get_by_id(
            session,
            student.id,
        )

        if updated_student is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Не удалось получить обновлённого ученика",
            )

        return updated_student

    async def archive(
        self,
        session: AsyncSession,
        student_id: int,
        current_user: User,
        archive_comment: str | None = None,
    ) -> Student:
        """Переводит ученика в архив."""

        student = await self.get_by_id(
            session,
            student_id,
            current_user,
        )

        student.status = StudentStatus.ARCHIVED

        if archive_comment is not None:
            student.comment = archive_comment

        await session.commit()
        await session.refresh(student)

        return student


student_service = StudentService()