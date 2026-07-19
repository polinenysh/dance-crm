from datetime import date

from fastapi import HTTPException, status

from app.modules.users.model import User


def resolve_branch_id(
    current_user: User,
    requested_branch_id: int | None,
) -> int | None:
    """Возвращает доступный пользователю филиал для отчёта."""

    if current_user.role.value == "owner":
        return requested_branch_id

    if current_user.role.value == "branch_admin":
        if current_user.branch_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Администратор не привязан к филиалу",
            )

        if requested_branch_id is not None and requested_branch_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к статистике другого филиала",
            )

        return current_user.branch_id

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для просмотра отчётов",
    )


def validate_period(date_from: date, date_to: date) -> None:
    """Проверяет корректность периода отчёта."""

    if date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="date_from не может быть позже date_to",
        )

    if (date_to - date_from).days > 366:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Период отчёта не может превышать 366 дней",
        )
