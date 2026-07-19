from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.branches.model import Branch
    from app.modules.dance_styles.model import DanceStyle
    from app.modules.schedule.model import Lesson, ScheduleSlot
    from app.modules.students.model import Student
    from app.modules.teachers.model import Teacher


class Group(IdMixin, TimestampMixin, Base):
    """Модель учебной группы."""

    __tablename__ = "groups"
    __table_args__ = (
        CheckConstraint(
            "max_students > 0 AND max_students <= 25",
            name="ck_groups_max_students_range",
        ),
        UniqueConstraint(
            "branch_id",
            "name",
            name="uq_groups_branch_name",
        ),
    )

    branch_id: Mapped[int] = mapped_column(
        ForeignKey(
            "branches.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    dance_style_id: Mapped[int] = mapped_column(
        ForeignKey(
            "dance_styles.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    teacher_id: Mapped[int] = mapped_column(
        ForeignKey(
            "teachers.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    max_students: Mapped[int] = mapped_column(
        default=25,
        server_default="25",
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    branch: Mapped["Branch"] = relationship(
        back_populates="groups",
    )

    dance_style: Mapped["DanceStyle"] = relationship(
        back_populates="groups",
    )

    teacher: Mapped["Teacher"] = relationship(
        back_populates="groups",
    )

    memberships: Mapped[list["GroupMembership"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )

    schedule_slots: Mapped[list["ScheduleSlot"]] = relationship(
        back_populates="group",
        cascade="all, delete-orphan",
    )

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="group",
    )


class GroupMembership(IdMixin, TimestampMixin, Base):
    """Модель членства ученика в группе."""

    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "student_id",
            name="uq_group_memberships_group_student",
        ),
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groups.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    student_id: Mapped[int] = mapped_column(
        ForeignKey(
            "students.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    left_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    group: Mapped["Group"] = relationship(
        back_populates="memberships",
    )

    student: Mapped["Student"] = relationship(
        back_populates="group_memberships",
    )
