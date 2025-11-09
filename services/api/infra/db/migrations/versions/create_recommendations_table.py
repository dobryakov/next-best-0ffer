"""Create recommendations and calculation_jobs tables."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_create_recommendations"
down_revision: str | None = "002_create_events"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

recommendation_status_enum = postgresql.ENUM(
    "pending",
    "ready",
    "failed",
    name="recommendation_status",
    create_type=False,
)

calculation_job_status_enum = postgresql.ENUM(
    "pending",
    "running",
    "completed",
    "failed",
    name="calculation_job_status",
    create_type=False,
)


def upgrade() -> None:
    recommendation_status_enum.create(op.get_bind(), checkfirst=True)
    calculation_job_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("customer_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "status",
            recommendation_status_enum,
            nullable=False,
            server_default=sa.text("'pending'::recommendation_status"),
        ),
        sa.Column(
            "offers",
            sa.JSON,
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("experiment_variant", sa.String(length=64), nullable=False, server_default="control"),
        sa.Column(
            "metadata",
            sa.JSON,
            nullable=False,
            server_default=sa.text("'{}'::json"),
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
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_recommendations_customer_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "uq_recommendations_customer",
        "recommendations",
        ["customer_id"],
        unique=True,
    )

    op.create_table(
        "calculation_jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("recommendation_id", sa.String(length=36), nullable=False),
        sa.Column("customer_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "status",
            calculation_job_status_enum,
            nullable=False,
            server_default=sa.text("'pending'::calculation_job_status"),
        ),
        sa.Column("requested_variant", sa.String(length=64), nullable=False),
        sa.Column("requested_channel", sa.String(length=64), nullable=True),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=512), nullable=True),
        sa.Column(
            "metadata",
            sa.JSON,
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendations.id"],
            name="fk_calculation_jobs_recommendation_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_calculation_jobs_customer_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_calculation_jobs_customer",
        "calculation_jobs",
        ["customer_id"],
    )
    op.create_index(
        "ix_calculation_jobs_active",
        "calculation_jobs",
        ["recommendation_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_calculation_jobs_active", table_name="calculation_jobs")
    op.drop_index("ix_calculation_jobs_customer", table_name="calculation_jobs")
    op.drop_table("calculation_jobs")

    op.drop_index("uq_recommendations_customer", table_name="recommendations")
    op.drop_table("recommendations")

    calculation_job_status_enum.drop(op.get_bind(), checkfirst=True)
    recommendation_status_enum.drop(op.get_bind(), checkfirst=True)


