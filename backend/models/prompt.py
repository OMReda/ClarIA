import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base, GUID


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("files.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        CheckConstraint(
            "status IN ('pending','processing','awaiting_clarification','completed','failed')"
        ),
        server_default="pending",
        nullable=False,
    )
    clarification_question: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    clarification_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    file: Mapped["File"] = relationship("File", back_populates="prompts")  # noqa: F821
    chart: Mapped[Optional["Chart"]] = relationship(  # noqa: F821
        "Chart", back_populates="prompt", uselist=False, cascade="all, delete-orphan"
    )
