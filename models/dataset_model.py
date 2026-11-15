from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class Dataset(BaseModel):
    """A pre-computed document the website reads whole: archive summaries, the harmonization
    validation, the GCC history summary and the fire-risk model (see DatasetName).
    """

    __tablename__ = "datasets"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    payload: Mapped[Any] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
