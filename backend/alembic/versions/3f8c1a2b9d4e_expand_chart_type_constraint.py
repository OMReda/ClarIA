"""expand chart_type check constraint to include area, radar, heatmap

Revision ID: 3f8c1a2b9d4e
Revises: 795420f44a86
Create Date: 2026-07-29
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '3f8c1a2b9d4e'
down_revision = '795420f44a86'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TABLE charts_new ("
        "  id TEXT NOT NULL PRIMARY KEY,"
        "  prompt_id TEXT NOT NULL UNIQUE REFERENCES prompts(id) ON DELETE CASCADE,"
        "  chart_type TEXT NOT NULL CHECK(chart_type IN ('bar','line','pie','scatter','histogram','area','radar','heatmap')),"
        "  chart_spec JSON NOT NULL,"
        "  created_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)"
        ")"
    )
    op.execute("INSERT INTO charts_new SELECT * FROM charts")
    op.execute("DROP TABLE charts")
    op.execute("ALTER TABLE charts_new RENAME TO charts")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_charts_prompt_id ON charts (prompt_id)")


def downgrade() -> None:
    op.execute(
        "CREATE TABLE charts_old ("
        "  id TEXT NOT NULL PRIMARY KEY,"
        "  prompt_id TEXT NOT NULL UNIQUE REFERENCES prompts(id) ON DELETE CASCADE,"
        "  chart_type TEXT NOT NULL CHECK(chart_type IN ('bar','line','pie','scatter','histogram')),"
        "  chart_spec JSON NOT NULL,"
        "  created_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)"
        ")"
    )
    op.execute("INSERT INTO charts_old SELECT * FROM charts WHERE chart_type IN ('bar','line','pie','scatter','histogram')")
    op.execute("DROP TABLE charts")
    op.execute("ALTER TABLE charts_old RENAME TO charts")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_charts_prompt_id ON charts (prompt_id)")
