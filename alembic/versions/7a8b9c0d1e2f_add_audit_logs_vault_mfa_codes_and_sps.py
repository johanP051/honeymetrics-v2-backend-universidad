"""add_audit_logs_vault_mfa_codes_and_sps

Revision ID: 7a8b9c0d1e2f
Revises: 511778dedd84
Create Date: 2026-11-01 13:30:00.000000

"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = '511778dedd84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Tabla blacklist_entries (si no fue creada previamente)
    if "blacklist_entries" not in existing_tables:
        op.create_table(
            "blacklist_entries",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("ip", sa.String(length=45), nullable=False),
            sa.Column("ip_type", sa.String(length=10), server_default="IPv4", nullable=False),
            sa.Column("country", sa.String(length=100), server_default="Unknown", nullable=False),
            sa.Column("threat_score", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("blocked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_blacklist_entries_ip", "blacklist_entries", ["ip"], unique=True)

    # 2. Tabla mfa_backup_codes
    if "mfa_backup_codes" not in existing_tables:
        op.create_table(
            "mfa_backup_codes",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("code_hash", sa.String(length=64), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_mfa_backup_codes_user_id", "mfa_backup_codes", ["user_id"], unique=False)
        op.create_index("ix_mfa_backup_codes_code_hash", "mfa_backup_codes", ["code_hash"], unique=False)

    # 3. Tabla blacklist_audit_vault
    if "blacklist_audit_vault" not in existing_tables:
        op.create_table(
            "blacklist_audit_vault",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("original_entry_id", sa.Integer(), nullable=False),
            sa.Column("original_ip", sa.String(length=45), nullable=False),
            sa.Column("ip_type", sa.String(length=10), nullable=True),
            sa.Column("country", sa.String(length=100), nullable=True),
            sa.Column("threat_score", sa.Integer(), nullable=False),
            sa.Column("category", sa.String(length=50), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("deleted_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("full_record_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("deleted_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_blacklist_audit_vault_original_ip", "blacklist_audit_vault", ["original_ip"], unique=False)

    # 4. Tabla audit_logs
    if "audit_logs" not in existing_tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("actor_email", sa.String(length=255), nullable=True),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("entity_name", sa.String(length=80), nullable=False),
            sa.Column("entity_id", sa.String(length=64), nullable=True),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_logs_action", "audit_logs", ["action"], unique=False)

    # 5. Columnas en users: auth_version y expansión de totp_secret
    user_columns = {col["name"] for col in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "auth_version" not in user_columns:
            batch_op.add_column(sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))
        if "totp_secret" in user_columns:
            batch_op.alter_column(
                "totp_secret",
                existing_type=sa.String(length=64),
                type_=sa.String(length=255),
                existing_nullable=True,
            )

    # 6. Inyección de 3 Triggers y 3 Stored Procedures en PostgreSQL 16
    if bind.dialect.name == "postgresql":
        sql_path = Path(__file__).resolve().parents[2] / "scripts" / "db_programmability_udec.sql"
        if sql_path.exists():
            sql_script = sql_path.read_text(encoding="utf-8")
            op.execute(sa.text(sql_script))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("""
            DROP PROCEDURE IF EXISTS sp_enforce_role_password_rotation_and_audit(VARCHAR, TEXT);
            DROP PROCEDURE IF EXISTS sp_escalate_and_consolidate_blacklist_threat(VARCHAR, INT, TEXT, INT);
            DROP PROCEDURE IF EXISTS sp_archive_and_purge_expired_exports_and_tokens(INT);

            DROP TRIGGER IF EXISTS trg_audit_user_security_changes ON users;
            DROP FUNCTION IF EXISTS fn_trg_audit_user_security_changes();

            DROP TRIGGER IF EXISTS trg_sanitize_and_validate_blacklist_ip ON blacklist_entries;
            DROP FUNCTION IF EXISTS fn_trg_sanitize_and_validate_blacklist_ip();

            DROP TRIGGER IF EXISTS trg_audit_deleted_blacklist_vault ON blacklist_entries;
            DROP FUNCTION IF EXISTS fn_trg_audit_blacklist_deletion();
        """))

    inspector = Inspector.from_engine(bind)
    existing_tables = set(inspector.get_table_names())

    if "audit_logs" in existing_tables:
        op.drop_table("audit_logs")
    if "blacklist_audit_vault" in existing_tables:
        op.drop_table("blacklist_audit_vault")
    if "mfa_backup_codes" in existing_tables:
        op.drop_table("mfa_backup_codes")
    if "blacklist_entries" in existing_tables:
        op.drop_table("blacklist_entries")

    user_columns = {col["name"] for col in inspector.get_columns("users")}
    with op.batch_alter_table("users") as batch_op:
        if "auth_version" in user_columns:
            batch_op.drop_column("auth_version")
        if "totp_secret" in user_columns:
            batch_op.alter_column(
                "totp_secret",
                existing_type=sa.String(length=255),
                type_=sa.String(length=64),
                existing_nullable=True,
            )
