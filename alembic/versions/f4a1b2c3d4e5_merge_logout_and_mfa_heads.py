"""merge logout denylist and MFA migration heads.

Revision ID: f4a1b2c3d4e5
Revises: b82e4a1f7c3d, d93c7b5e2f1a
Create Date: 2026-10-07
"""

from typing import Sequence, Union


revision: str = "f4a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = (
    "b82e4a1f7c3d",
    "d93c7b5e2f1a",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge the already-applied logout and MFA schema branches."""


def downgrade() -> None:
    """Keep the merge revision reversible without changing either branch."""
