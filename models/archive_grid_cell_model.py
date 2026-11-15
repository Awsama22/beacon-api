from sqlalchemy import Integer, SmallInteger
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class ArchiveGridCell(BaseModel):
    """One 0.5° cell of the globe layer: harmonized hot spots per year since 2000.

    `row` counts from 90°N and `col` from 180°W.
    """

    __tablename__ = "archive_grid_cells"

    row: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    col: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    yearly: Mapped[list[int]] = mapped_column(ARRAY(Integer))
