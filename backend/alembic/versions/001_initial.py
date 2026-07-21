"""Initial schema — sessions, files, prompts, charts."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("session_id", sa.String(length=36), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.Text, nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("sheet_name", sa.Text, nullable=True),
        sa.Column("storage_path", sa.Text, nullable=False),
        sa.Column("columns_metadata", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="uploaded"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("file_type IN ('csv', 'xlsx', 'xls')", name="ck_files_file_type"),
        sa.CheckConstraint("status IN ('uploaded','needs_sheet_selection','validated','error')", name="ck_files_status"),
    )

    op.create_table(
        "prompts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("file_id", sa.String(length=36), sa.ForeignKey("files.id", ondelete="CASCADE"), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        sa.Column("clarification_question", sa.Text, nullable=True),
        sa.Column("clarification_answer", sa.Text, nullable=True),
        sa.Column("generated_code", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','processing','awaiting_clarification','completed','failed')",
            name="ck_prompts_status",
        ),
    )

    op.create_table(
        "charts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("prompt_id", sa.String(length=36), sa.ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("chart_type", sa.Text, nullable=False),
        sa.Column("chart_spec", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("chart_type IN ('bar','line','pie','scatter','histogram')", name="ck_charts_chart_type"),
    )

    # Indexes
    op.create_index("ix_files_session_id", "files", ["session_id"])
    op.create_index("ix_prompts_file_id", "prompts", ["file_id"])
    op.create_index("ix_charts_prompt_id", "charts", ["prompt_id"])


def downgrade() -> None:
    op.drop_table("charts")
    op.drop_table("prompts")
    op.drop_table("files")
    op.drop_table("sessions")
