from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin
from app.modules.teachers.model import teacher_dance_styles

if TYPE_CHECKING:
    from app.modules.teachers.model import Teacher
    from app.modules.groups.model import Group


class DanceStyle(IdMixin, TimestampMixin, Base):
    """Модель танцевального направления."""

    __tablename__ = "dance_styles"

    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    teachers: Mapped[list["Teacher"]] = relationship(
        secondary=teacher_dance_styles,
        back_populates="dance_styles",
    )

    groups: Mapped[list["Group"]] = relationship(
        back_populates="dance_style",
    )