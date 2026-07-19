from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IdMixin, TimestampMixin

if TYPE_CHECKING:
    from app.modules.students.model import Student


class Parent(IdMixin, TimestampMixin, Base):
    """Модель родителя или законного представителя ученика."""

    __tablename__ = "parents"

    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        String(12),
        unique=True,
        index=True,
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    students: Mapped[list["Student"]] = relationship(
        back_populates="parent",
    )
