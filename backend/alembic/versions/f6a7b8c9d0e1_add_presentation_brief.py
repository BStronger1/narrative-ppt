"""Persist presentation brief separately from evidence sources."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "projects",
        sa.Column(
            "brief", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
    )


def downgrade():
    op.drop_column("projects", "brief")
