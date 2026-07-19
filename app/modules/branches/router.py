from fastapi import APIRouter, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import CurrentUserDep, OwnerDep
from app.modules.branches.schemas import BranchCreate, BranchResponse, BranchUpdate
from app.modules.branches.service import branch_service

router = APIRouter(prefix="/branches", tags=["Branches"])


@router.get("", response_model=list[BranchResponse])
async def get_branches(session: SessionDep, _: CurrentUserDep) -> list[BranchResponse]:
    """Возвращает список филиалов авторизованному сотруднику."""
    return await branch_service.get_all(session)


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(data: BranchCreate, session: SessionDep, _: OwnerDep) -> BranchResponse:
    """Создаёт филиал. Доступно только владельцу."""
    return await branch_service.create(session, data)


@router.get("/{branch_id}", response_model=BranchResponse)
async def get_branch(branch_id: int, session: SessionDep, _: CurrentUserDep) -> BranchResponse:
    """Возвращает филиал."""
    return await branch_service.get_by_id(session, branch_id)


@router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(branch_id: int, data: BranchUpdate, session: SessionDep, _: OwnerDep) -> BranchResponse:
    """Обновляет филиал. Доступно только владельцу."""
    return await branch_service.update(session, branch_id, data)
