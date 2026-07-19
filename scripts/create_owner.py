import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models  # noqa: F401
from app.db.session import async_session_factory
from app.modules.auth.security import hash_password
from app.modules.users.model import User
from app.modules.users.repository import user_repository
from app.shared.enums import UserRole


async def create_owner() -> None:
    """Создаёт первоначальную учётную запись руководителя."""

    email = input("Email: ").strip().lower()
    password = input("Password: ").strip()
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()

    async with async_session_factory() as session:
        session: AsyncSession

        existing_user = await user_repository.get_by_email(
            session,
            email,
        )

        if existing_user is not None:
            print("Пользователь с таким email уже существует")
            return

        owner = User(
            email=email,
            hashed_password=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            phone=None,
            role=UserRole.OWNER,
            branch_id=None,
            is_active=True,
        )

        session.add(owner)
        await session.commit()

        print("Руководитель успешно создан")


if __name__ == "__main__":
    asyncio.run(create_owner())
