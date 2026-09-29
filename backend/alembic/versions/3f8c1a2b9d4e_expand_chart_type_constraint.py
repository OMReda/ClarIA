"""expand chart_type check constraint to include area, radar, heatmap

Revision ID: 3f8c1a2b9d4e
Revises: 795420f44a86
Create Date: 2026-07-29

NOTE: Alembic's render_as_batch=True in env.py enables batch mode for SQLite.
For PostgreSQL we can use DROP CONSTRAINT / ADD CONSTRAINT directly; both
branches are handled below via dialect detection so this migration works in
all environments.
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = '3f8c1a2b9d4e'
down_revision = '795420f44a86'
branch_labels = None
depends_on = None

_NEW_VALUES = "('bar','line','pie','scatter','histogram','area','radar','heatmap')"
_OLD_VALUES = "('bar','line','pie','scatter','histogram')"
_CONSTRAINT = "ck_charts_chart_type"


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        # PostgreSQL supports ALTER TABLE DROP/ADD CONSTRAINT directly.
        op.drop_constraint(_CONSTRAINT, "charts", type_="check")
        op.create_check_constraint(
            _CONSTRAINT,
            "charts",
            sa.text(f"chart_type IN {_NEW_VALUES}"),
        )
    else:
        # SQLite (dev / tests): use Alembic batch mode which rebuilds the table.
        with op.batch_alter_table("charts") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT, type_="check")
            batch_op.create_check_constraint(
                _CONSTRAINT,
                sa.text(f"chart_type IN {_NEW_VALUES}"),
            )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        # Remove rows that would violate the narrower constraint before restoring it.
        op.execute(
            "DELETE FROM charts WHERE chart_type NOT IN ('bar','line','pie','scatter','histogram')"
        )
        op.drop_constraint(_CONSTRAINT, "charts", type_="check")
        op.create_check_constraint(
            _CONSTRAINT,
            "charts",
            sa.text(f"chart_type IN {_OLD_VALUES}"),
        )
    else:
        op.execute(
            "DELETE FROM charts WHERE chart_type NOT IN ('bar','line','pie','scatter','histogram')"
        )
        with op.batch_alter_table("charts") as batch_op:
            batch_op.drop_constraint(_CONSTRAINT, type_="check")
            batch_op.create_check_constraint(
                _CONSTRAINT,
                sa.text(f"chart_type IN {_OLD_VALUES}"),
            )
