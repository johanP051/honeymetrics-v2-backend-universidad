"""expand_role_description_to_255

Revision ID: 511778dedd84
Revises: f4a1b2c3d4e5
Create Date: 2026-10-12 13:15:35.871371

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '511778dedd84'
down_revision: Union[str, Sequence[str], None] = 'f4a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: expand roles.description from 50 to 255 chars."""
    op.alter_column(
        'roles',
        'description',
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=255),
        existing_nullable=True
    )


def downgrade() -> None:
    """Downgrade schema: shrink roles.description back to 50 chars."""
    op.alter_column(
        'roles',
        'description',
        existing_type=sa.VARCHAR(length=255),
        type_=sa.String(length=50),
        existing_nullable=True
    )
