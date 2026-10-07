"""add revoked_tokens denylist logout (port de guia)

Revision ID: b82e4a1f7c3d
Revises: 1d8d9ec8ed77
Create Date: 2026-10-07

Nota: si la rama SMTP (14779f70ed05) se mergea primero, crear
revision merge que una ambas cabezas.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b82e4a1f7c3d"
down_revision: Union[str, Sequence[str], None] = "1d8d9ec8ed77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("token_jti", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_revoked_tokens_token_jti", "revoked_tokens", ["token_jti"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_revoked_tokens_token_jti", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
