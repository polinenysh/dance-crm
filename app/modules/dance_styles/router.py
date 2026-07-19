from fastapi import APIRouter, Query, status

from app.db.session import SessionDep
from app.modules.auth.dependencies import CurrentUserDep, OwnerDep
from app.modules.dance_styles.schemas import (
    DanceStyleCreate,
    DanceStyleResponse,
    DanceStyleUpdate,
)
from app.modules.dance_styles.service import dance_style_service

router = APIRouter(
    prefix="/dance-styles",
    tags=["Dance styles"],
)


@router.get(
    "",
    response_model=list[DanceStyleResponse],
)
async def get_dance_styles(
    session: SessionDep,
    _: CurrentUserDep,
    active_only: bool = Query(default=False),
) -> list[DanceStyleResponse]:
    """Возвращает список танцевальных направлений."""

    return await dance_style_service.get_all(
        session,
        active_only,
    )


@router.post(
    "",
    response_model=DanceStyleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dance_style(
    data: DanceStyleCreate,
    session: SessionDep,
    _: OwnerDep,
) -> DanceStyleResponse:
    """Создаёт танцевальное направление."""

    return await dance_style_service.create(
        session,
        data,
    )


@router.get(
    "/{dance_style_id}",
    response_model=DanceStyleResponse,
)
async def get_dance_style(
    dance_style_id: int,
    session: SessionDep,
    _: CurrentUserDep,
) -> DanceStyleResponse:
    """Возвращает направление по идентификатору."""

    return await dance_style_service.get_by_id(
        session,
        dance_style_id,
    )


@router.patch(
    "/{dance_style_id}",
    response_model=DanceStyleResponse,
)
async def update_dance_style(
    dance_style_id: int,
    data: DanceStyleUpdate,
    session: SessionDep,
    _: OwnerDep,
) -> DanceStyleResponse:
    """Обновляет танцевальное направление."""

    return await dance_style_service.update(
        session,
        dance_style_id,
        data,
    )
