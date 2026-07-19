from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.branches.model import Branch
    from app.modules.schedule.model import Lesson, ScheduleSlot


class Hall(IdMixin, TimestampMixin, Base):
    '''Модель зала'''
    __tablename__ = "halls"
    __table_args__ = (
        CheckConstraint(
            "capacity > 0",
            name="ck_halls_capacity_positive",
        ),
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey("branches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    capacity: Mapped[int] = mapped_column(
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    branch: Mapped["Branch"] = relationship(
        back_populates="halls",
    )

    schedule_slots: Mapped[list["ScheduleSlot"]] = relationship(
        back_populates="hall",
    )

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="hall",
    )