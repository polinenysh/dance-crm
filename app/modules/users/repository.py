from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.model import User
from app.modules.users.schemas import UserCreate, UserUpdate
from app.shared.repository import BaseRepository


class UserRepository(
    BaseRepository[
        User,
        UserCreate,
        UserUpdate,
    ]
):
    """Репозиторий для работы с сотрудниками."""

    def __init__(self) -> None:
        """Инициализирует репозиторий сотрудников."""

        super().__init__(User)

    async def get_all(
        self,
        session: AsyncSession,
        branch_id: int | None = None,
    ) -> list[User]:
        """Возвращает сотрудников с фильтрацией по филиалу."""

        query = select(User).order_by(
            User.last_name,
            User.first_name,
        )

        if branch_id is not None:
            query = query.where(User.branch_id == branch_id)

        result = await session.scalars(query)
        return list(result.all())

    async def get_by_email(
        self,
        session: AsyncSession,
        email: str,
    ) -> User | None:
        """Возвращает сотрудника по адресу электронной почты."""

        result = await session.scalars(select(User).where(User.email == email.lower()))
        return result.first()

    async def create_with_password(
        self,
        session: AsyncSession,
        data: UserCreate,
        hashed_password: str,
    ) -> User:
        """Создаёт сотрудника с готовым хешем пароля."""

        user_data = data.model_dump(exclude={"password"})
        user_data["email"] = data.email.lower()

        user = User(
            **user_data,
            hashed_password=hashed_password,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user


user_repository = UserRepository()
