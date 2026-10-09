"""add worker leases and durable agent steps

Revision ID: 6f74b81a9210
Revises: 0dada3bb9c31
Create Date: 2026-10-09 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6f74b81a9210"
down_revision: str | None = "0dada3bb9c31"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    run_columns = {column["name"] for column in inspector.get_columns("agent_runs")}
    run_indexes = {index["name"] for index in inspector.get_indexes("agent_runs")}
    with op.batch_alter_table("agent_runs") as batch_op:
        if "queued_at" not in run_columns:
            batch_op.add_column(sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
        if "lease_owner" not in run_columns:
            batch_op.add_column(sa.Column("lease_owner", sa.String(length=120), nullable=True))
        if "lease_expires_at" not in run_columns:
            batch_op.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
        if "heartbeat_at" not in run_columns:
            batch_op.add_column(sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
        if "fencing_token" not in run_columns:
            batch_op.add_column(sa.Column(
                "fencing_token", sa.Integer(), nullable=False, server_default="0"
            ))
        if "ix_agent_runs_queued_at" not in run_indexes:
            batch_op.create_index("ix_agent_runs_queued_at", ["queued_at"])
        if "ix_agent_runs_lease_owner" not in run_indexes:
            batch_op.create_index("ix_agent_runs_lease_owner", ["lease_owner"])
        if "ix_agent_runs_lease_expires_at" not in run_indexes:
            batch_op.create_index("ix_agent_runs_lease_expires_at", ["lease_expires_at"])
    op.execute("UPDATE agent_runs SET queued_at = created_at WHERE queued_at IS NULL")

    tables = set(inspector.get_table_names())
    if "agent_steps" not in tables:
        op.create_table(
            "agent_steps",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("agent_run_id", sa.String(length=64), nullable=False),
            sa.Column("step_index", sa.Integer(), nullable=False),
            sa.Column("step_type", sa.String(length=64), nullable=False),
            sa.Column("input_hash", sa.String(length=64), nullable=False),
            sa.Column("output_hash", sa.String(length=64), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("attempt", sa.Integer(), nullable=False),
            sa.Column("payload", sa.Text(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("error_category", sa.String(length=120), nullable=True),
            sa.ForeignKeyConstraint(
                ["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("agent_run_id", "step_index", name="uq_agent_step_index"),
        )
        step_indexes: set[str] = set()
    else:
        step_indexes = {index["name"] for index in inspector.get_indexes("agent_steps")}
    for name, columns in (
        ("ix_agent_steps_agent_run_id", ["agent_run_id"]),
        ("ix_agent_steps_step_type", ["step_type"]),
        ("ix_agent_steps_status", ["status"]),
        ("ix_agent_steps_error_category", ["error_category"]),
    ):
        if name not in step_indexes:
            op.create_index(name, "agent_steps", columns)


def downgrade() -> None:
    op.drop_index("ix_agent_steps_error_category", table_name="agent_steps")
    op.drop_index("ix_agent_steps_status", table_name="agent_steps")
    op.drop_index("ix_agent_steps_step_type", table_name="agent_steps")
    op.drop_index("ix_agent_steps_agent_run_id", table_name="agent_steps")
    op.drop_table("agent_steps")
    with op.batch_alter_table("agent_runs") as batch_op:
        batch_op.drop_index("ix_agent_runs_lease_expires_at")
        batch_op.drop_index("ix_agent_runs_lease_owner")
        batch_op.drop_index("ix_agent_runs_queued_at")
        batch_op.drop_column("fencing_token")
        batch_op.drop_column("heartbeat_at")
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("lease_owner")
        batch_op.drop_column("queued_at")
