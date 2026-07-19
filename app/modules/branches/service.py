from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.branches.model import Branch
from app.modules.branches.repository import branch_repository
from app.modules.branches.schemas import BranchCreate, BranchUpdate


class BranchService:
    """Сервис бизнес-логики филиалов."""

    def __init__(self) -> None:
        """Инициализирует сервис филиалов."""
        self.repository = branch_repository

    async def get_all(
        self,
        session: AsyncSession,
    ) -> list[Branch]:
        return await self.repository.get_all(session)

    async def get_by_id(
        self,
        session: AsyncSession,
        branch_id: int,
    ) -> Branch:
        branch = await self.repository.get_by_id(
            session,
            branch_id,
        )

        if branch is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Филиал не найден",
            )

        return branch

    async def create(
        self,
        session: AsyncSession,
        data: BranchCreate,
    ) -> Branch:
        existing_branch = await self.repository.get_by_name(
            session,
            data.name,
        )

        if existing_branch is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Филиал с таким названием уже существует",
            )

        return await self.repository.create(session, data)

    async def update(
        self,
        session: AsyncSession,
        branch_id: int,
        data: BranchUpdate,
    ) -> Branch:
        branch = await self.get_by_id(session, branch_id)

        if data.name is not None and data.name != branch.name:
            existing_branch = await self.repository.get_by_name(
                session,
                data.name,
            )

            if existing_branch is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Филиал с таким названием уже существует",
                )

        return await self.repository.update(
            session,
            branch,
            data,
        )


branch_service = BranchService()