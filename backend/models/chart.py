import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base, GUID


class Chart(Base):
    __tablename__ = "charts"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(), primary_key=True, default=uuid.uuid4
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    chart_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("chart_type IN ('bar','line','pie','scatter','histogram','area','radar','heatmap')"),
        nullable=False,
    )
    chart_spec: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    prompt: Mapped["Prompt"] = relationship("Prompt", back_populates="chart")  # noqa: F821
