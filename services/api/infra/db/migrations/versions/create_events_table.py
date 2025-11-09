"""Create events table with idempotency support."""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_create_events"
down_revision: str | None = "001_create_customers"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

event_category_enum = postgresql.ENUM(
    "view",
    "search",
    "add_to_cart",
    "purchase",
    name="event_category",
    create_type=False,
)


def upgrade() -> None:
    event_category_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("idempotency_token", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "category",
            sa.Enum("view", "search", "add_to_cart", "purchase", name="event_category"),
            nullable=False,
        ),
        sa.Column("customer_id", sa.String(length=36), nullable=False),
        sa.Column(
            "product_ids",
            sa.JSON,
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "payload",
            sa.JSON,
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
            name="fk_events_customer_id",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_events_customer_category",
        "events",
        ["customer_id", "category"],
    )
    op.create_index(
        "ix_events_ingested_at",
        "events",
        ["ingested_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_events_ingested_at", table_name="events")
    op.drop_index("ix_events_customer_category", table_name="events")
    op.drop_table("events")
    event_category_enum.drop(op.get_bind(), checkfirst=True)


