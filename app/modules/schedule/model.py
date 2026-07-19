from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.shared.enums import LessonStatus, Weekday

if TYPE_CHECKING:
    from app.modules.attendance.model import Attendance
    from app.modules.groups.model import Group
    from app.modules.halls.model import Hall
    from app.modules.subscriptions.model import SubscriptionExtension
    from app.modules.teachers.model import Teacher
    from app.modules.users.model import User


class ScheduleSlot(IdMixin, TimestampMixin, Base):
    """Модель повторяющегося элемента расписания."""

    __tablename__ = "schedule_slots"
    __table_args__ = (
        CheckConstraint(
            "weekday >= 0 AND weekday <= 6",
            name="ck_schedule_slots_weekday_range",
        ),
        CheckConstraint(
            "start_time < end_time",
            name="ck_schedule_slots_time_range",
        ),
        UniqueConstraint(
            "group_id",
            "weekday",
            "start_time",
            name="uq_schedule_slots_group_weekday_start",
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

    hall_id: Mapped[int] = mapped_column(
        ForeignKey(
            "halls.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    weekday: Mapped[Weekday] = mapped_column(
        Integer,
        nullable=False,
    )

    start_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    end_time: Mapped[time] = mapped_column(
        Time,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    group: Mapped["Group"] = relationship(
        back_populates="schedule_slots",
    )

    hall: Mapped["Hall"] = relationship(
        back_populates="schedule_slots",
    )

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="schedule_slot",
    )


class Lesson(IdMixin, TimestampMixin, Base):
    """Модель конкретного занятия."""

    __tablename__ = "lessons"
    __table_args__ = (
        CheckConstraint(
            "starts_at < ends_at",
            name="ck_lessons_datetime_range",
        ),
        UniqueConstraint(
            "schedule_slot_id",
            "starts_at",
            name="uq_lessons_schedule_slot_starts_at",
        ),
    )

    schedule_slot_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "schedule_slots.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey(
            "groups.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    hall_id: Mapped[int] = mapped_column(
        ForeignKey(
            "halls.id",
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

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    ends_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[LessonStatus] = mapped_column(
        Enum(
            LessonStatus,
            name="lesson_status",
            values_callable=lambda enum_class: [item.value for item in enum_class],
        ),
        default=LessonStatus.PLANNED,
        server_default=LessonStatus.PLANNED.value,
        nullable=False,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    cancelled_by_studio: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    cancelled_by: Mapped[int | None] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    attendances: Mapped[list["Attendance"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
    )

    schedule_slot: Mapped["ScheduleSlot | None"] = relationship(
        back_populates="lessons",
    )

    group: Mapped["Group"] = relationship(
        back_populates="lessons",
    )

    hall: Mapped["Hall"] = relationship(
        back_populates="lessons",
    )

    teacher: Mapped["Teacher"] = relationship(
        back_populates="lessons",
    )

    cancelled_by_user: Mapped["User | None"] = relationship(
        foreign_keys=[cancelled_by],
    )

    subscription_extensions: Mapped[list["SubscriptionExtension"]] = relationship(
        back_populates="lesson",
    )
