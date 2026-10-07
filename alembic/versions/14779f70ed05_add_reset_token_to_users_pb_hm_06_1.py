"""add reset_token to users PB-HM-06.1

Revision ID: 14779f70ed05
Revises: 1d8d9ec8ed77
Create Date: 2026-10-06 19:05:50.196564

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14779f70ed05'
down_revision: Union[str, Sequence[str], None] = '1d8d9ec8ed77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("reset_token", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("reset_token_expires", sa.DateTime(), nullable=True))
    op.create_unique_constraint("uq_users_reset_token", "users", ["reset_token"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_users_reset_token", "users", type_="unique")
    op.drop_column("users", "reset_token_expires")
    op.drop_column("users", "reset_token")
