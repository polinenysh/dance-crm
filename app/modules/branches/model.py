from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.halls.model import Hall
    from app.modules.students.model import Student
    from app.modules.users.model import User
    from app.modules.groups.model import Group
    from app.modules.subscription_plans.model import SubscriptionPlan
    from app.modules.subscriptions.model import StudentSubscription
    from app.modules.payments.model import Payment


class Branch(IdMixin, TimestampMixin, Base):
    '''Модель филиала'''
    __tablename__ = "branches"

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
    )

    address: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(12),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    halls: Mapped[list["Hall"]] = relationship(
        back_populates="branch",
        cascade="all, delete-orphan",
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="branch",
    )

    students: Mapped[list["Student"]] = relationship(
        back_populates="branch",
    )

    groups: Mapped[list["Group"]] = relationship(
        back_populates="branch",
    )

    subscription_plans: Mapped[list["SubscriptionPlan"]] = relationship(
        back_populates="branch",
    )

    student_subscriptions: Mapped[list["StudentSubscription"]] = relationship(
        back_populates="branch",
    )
    
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="branch",
    )