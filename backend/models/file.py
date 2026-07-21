import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base, GUID


class File(Base):
    __tablename__ = "files"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    owner_id: Mapped[str] = mapped_column(
        String(36),
        index=True,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(
        String(10),
        CheckConstraint("file_type IN ('csv', 'xlsx', 'xls')"),
        nullable=False,
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sheet_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    columns_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    preview_rows: Mapped[Optional[list[dict]]] = mapped_column(JSON, nullable=True)
    dashboard_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(30),
        CheckConstraint(
            "status IN ('uploaded','needs_sheet_selection','validated','error')"
        ),
        server_default="uploaded",
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompts: Mapped[list["Prompt"]] = relationship(  # noqa: F821
        "Prompt", back_populates="file", cascade="all, delete-orphan"
    )
