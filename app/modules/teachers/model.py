from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.dance_styles.model import DanceStyle
    from app.modules.groups.model import Group
    from app.modules.schedule.model import Lesson


teacher_dance_styles = Table(
    "teacher_dance_styles",
    Base.metadata,
    Column(
        "teacher_id",
        ForeignKey("teachers.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "dance_style_id",
        ForeignKey("dance_styles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Teacher(IdMixin, TimestampMixin, Base):
    """Модель преподавателя без учётной записи CRM."""

    __tablename__ = "teachers"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(12), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    dance_styles: Mapped[list["DanceStyle"]] = relationship(
        secondary=teacher_dance_styles,
        back_populates="teachers",
    )
    groups: Mapped[list["Group"]] = relationship(back_populates="teacher")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="teacher")
