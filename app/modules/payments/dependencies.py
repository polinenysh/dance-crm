from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.payments.repository import PaymentRepository
from app.modules.payments.service import PaymentService


def get_payment_repository(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
) -> PaymentRepository:
    """Возвращает репозиторий оплат."""

    return PaymentRepository(session)


def get_payment_service(
    session: Annotated[
        AsyncSession,
        Depends(get_session),
    ],
    repository: Annotated[
        PaymentRepository,
        Depends(get_payment_repository),
    ],
) -> PaymentService:
    """Возвращает сервис оплат."""

    return PaymentService(
        session=session,
        repository=repository,
    )


PaymentServiceDependency = Annotated[
    PaymentService,
    Depends(get_payment_service),
]
