from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.security import hash_password
from app.modules.branches.repository import branch_repository
from app.modules.users.model import User
from app.modules.users.repository import user_repository
from app.modules.users.schemas import UserCreate, UserUpdate
from app.shared.enums import UserRole


class UserService:
    """Сервис бизнес-логики сотрудников."""

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
    ) -> list[User]:
        """Возвращает список сотрудников."""

        return await user_repository.get_all(
            session,
            branch_id,
        )

    async def get_by_id(
        self,
        session: AsyncSession,
        user_id: int,
    ) -> User:
        """Возвращает сотрудника или ошибку 404."""

        user = await user_repository.get_by_id(
            session,
            user_id,
        )

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Сотрудник не найден",
            )

        return user

    async def create(
        self,
        session: AsyncSession,
        data: UserCreate,
    ) -> User:
        """Создаёт учётную запись сотрудника."""

        existing_user = await user_repository.get_by_email(
            session,
            data.email,
        )

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Пользователь с таким email уже существует",
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
                    detail="Нельзя назначить неактивный филиал",
                )

        hashed_password = hash_password(data.password)

        return await user_repository.create_with_password(
            session,
            data,
            hashed_password,
        )

    async def update(
        self,
        session: AsyncSession,
        user_id: int,
        data: UserUpdate,
    ) -> User:
        """Обновляет данные сотрудника."""

        user = await self.get_by_id(session, user_id)

        if data.email is not None:
            existing_user = await user_repository.get_by_email(
                session,
                data.email,
            )

            if (
                existing_user is not None
                and existing_user.id != user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Пользователь с таким email уже существует",
                )

            data.email = data.email.lower()

        target_role = data.role or user.role

        if "branch_id" in data.model_fields_set:
            target_branch_id = data.branch_id
        else:
            target_branch_id = user.branch_id

        if target_role == UserRole.BRANCH_ADMIN:
            if target_branch_id is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Администратору необходимо назначить филиал",
                )

        if target_role == UserRole.OWNER and target_branch_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Руководитель не должен быть привязан к филиалу",
            )

        if target_branch_id is not None:
            branch = await branch_repository.get_by_id(
                session,
                target_branch_id,
            )

            if branch is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Филиал не найден",
                )

        return await user_repository.update(
            session,
            user,
            data,
        )


user_service = UserService()