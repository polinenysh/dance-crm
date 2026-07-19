"""add timezone to group membership dates

Revision ID: c43f3dc502be
Revises: b8c6664eef82
Create Date: 2026-07-16 19:19:59.731275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c43f3dc502be'
down_revision: Union[str, Sequence[str], None] = 'b8c6664eef82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Добавляет часовой пояс датам членства в группе."""

    op.alter_column(
        "group_memberships",
        "joined_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="joined_at AT TIME ZONE 'UTC'",
    )

    op.alter_column(
        "group_memberships",
        "left_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="left_at AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    """Убирает часовой пояс у дат членства в группе."""

    op.alter_column(
        "group_memberships",
        "left_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="left_at AT TIME ZONE 'UTC'",
    )

    op.alter_column(
        "group_memberships",
        "joined_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="joined_at AT TIME ZONE 'UTC'",
    )
