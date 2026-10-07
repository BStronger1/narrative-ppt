"""Persist audience narrative plans alongside outlines."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("project_outlines", sa.Column("narrative", postgresql.JSONB(), nullable=True))


def downgrade():
    op.drop_column("project_outlines", "narrative")
