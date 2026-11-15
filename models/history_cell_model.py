from sqlalchemy import Float, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class HistoryCell(BaseModel):
    """One 0.25° GCC cell of the burn history: hot spots per year and per calendar month."""

    __tablename__ = "history_cells"

    latitude: Mapped[float] = mapped_column(Float, primary_key=True)
    longitude: Mapped[float] = mapped_column(Float, primary_key=True)
    country: Mapped[str] = mapped_column(String(64))
    annual: Mapped[list[float]] = mapped_column(ARRAY(Float))
    monthly: Mapped[list[float]] = mapped_column(ARRAY(Float))
    total: Mapped[float] = mapped_column(Float)
