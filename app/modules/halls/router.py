from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import AdminOrOwnerDep
from app.modules.halls.schemas import HallCreate, HallResponse, HallUpdate
from app.modules.halls.service import hall_service

router = APIRouter(prefix="/halls", tags=["Halls"])


@router.get("", response_model=list[HallResponse])
async def get_halls(
    session: SessionDep, current_user: AdminOrOwnerDep, branch_id: int | None = Query(default=None, gt=0)
) -> list[HallResponse]:
    """Возвращает доступные сотруднику залы."""
    return await hall_service.get_all(session, current_user, branch_id)


@router.post("", response_model=HallResponse, status_code=status.HTTP_201_CREATED)
async def create_hall(data: HallCreate, session: SessionDep, current_user: AdminOrOwnerDep) -> HallResponse:
    """Создаёт зал в доступном филиале."""
    return await hall_service.create(session, data, current_user)


@router.get("/{hall_id}", response_model=HallResponse)
async def get_hall(hall_id: int, session: SessionDep, current_user: AdminOrOwnerDep) -> HallResponse:
    """Возвращает зал с проверкой филиала."""
    return await hall_service.get_by_id(session, hall_id, current_user)


@router.patch("/{hall_id}", response_model=HallResponse)
async def update_hall(
    hall_id: int, data: HallUpdate, session: SessionDep, current_user: AdminOrOwnerDep
) -> HallResponse:
    """Обновляет зал в доступном филиале."""
    return await hall_service.update(session, hall_id, data, current_user)
