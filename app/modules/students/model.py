from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.shared.enums import StudentStatus

if TYPE_CHECKING:
    from app.modules.attendance.model import Attendance
    from app.modules.branches.model import Branch
    from app.modules.groups.model import GroupMembership
    from app.modules.parents.model import Parent
    from app.modules.payments.model import Payment
    from app.modules.subscriptions.model import StudentSubscription
    from app.modules.users.model import User


class Student(IdMixin, TimestampMixin, Base):
    """Модель ученика детской школы танцев."""

    __tablename__ = "students"

    parent_id: Mapped[int] = mapped_column(
        ForeignKey(
            "parents.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    birth_date: Mapped[date | None] = mapped_column(
        nullable=True,
    )

    status: Mapped[StudentStatus] = mapped_column(
        Enum(
            StudentStatus,
            name="student_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=StudentStatus.ACTIVE,
        server_default=StudentStatus.ACTIVE.value,
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    parent: Mapped["Parent"] = relationship(
        back_populates="students",
    )

    branch: Mapped["Branch"] = relationship(
        back_populates="students",
    )

    creator: Mapped["User | None"] = relationship()

    group_memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="student",
    )

    subscriptions: Mapped[list["StudentSubscription"]] = relationship(
        back_populates="student",
    )

    attendances: Mapped[list["Attendance"]] = relationship(
        back_populates="student",
    )

    payments: Mapped[list["Payment"]] = relationship(
        back_populates="student",
    )
