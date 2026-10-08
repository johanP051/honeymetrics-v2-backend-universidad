"""add totp_secret and is_mfa_enabled for 2FA PB-HM-07.1

Revision ID: d93c7b5e2f1a
Revises: c71d8e2f9a04
Create Date: 2026-10-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d93c7b5e2f1a"
down_revision: Union[str, Sequence[str], None] = "c71d8e2f9a04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("is_mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("users", "is_mfa_enabled")
    op.drop_column("users", "totp_secret")
