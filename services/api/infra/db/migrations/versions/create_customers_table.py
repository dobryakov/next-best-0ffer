"""Create customers core tables with audit trail."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_create_customers"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


customer_state_enum = postgresql.ENUM(
    "new",
    "active",
    "suppressed",
    name="customer_state",
    create_type=False,
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    customer_state_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "customers",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("segments", sa.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("attributes", sa.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "state",
            sa.Enum("new", "active", "suppressed", name="customer_state"),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "uq_customers_email",
        "customers",
        ["email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "uq_customers_phone",
        "customers",
        ["phone"],
        unique=True,
        postgresql_where=sa.text("phone IS NOT NULL"),
    )
    op.create_index("ix_customers_state", "customers", ["state"])

    op.create_table(
        "customers_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_customers_audit_customer_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_customers_audit_logs_customer_id",
        "customers_audit_logs",
        ["customer_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_customers_audit_logs_customer_id", table_name="customers_audit_logs")
    op.drop_table("customers_audit_logs")

    op.drop_index("ix_customers_state", table_name="customers")
    op.drop_index("uq_customers_phone", table_name="customers")
    op.drop_index("uq_customers_email", table_name="customers")
    op.drop_table("customers")

    customer_state_enum.drop(op.get_bind(), checkfirst=True)


