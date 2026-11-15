from sqlalchemy import Float, Integer, SmallInteger
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class ArchiveCell(BaseModel):
    """One 0.25° cell of the harmonized MODIS + VIIRS archive since 2000.

    `row` counts from 90°N and `col` from 180°W. `modis` and `viirs` are sparse monthly
    counts as [month_index, count, month_index, count, ...], month_index 0 being January 2000.
    `ratio` is the cell's VIIRS-to-MODIS calibration and `country_index` points into the
    archive_countries dataset's countryNames (-1 for none).
    """

    __tablename__ = "archive_cells"

    row: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    col: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    ratio: Mapped[float] = mapped_column(Float)
    country_index: Mapped[int] = mapped_column(SmallInteger)
    modis: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    viirs: Mapped[list[int]] = mapped_column(ARRAY(Integer))
