from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from models.base_model import BaseModel


class StaticSource(BaseModel):
    """A known static heat source (gas flare, industry, volcano) on a 0.01° grid.

    Keys are latitude and longitude times 100, rounded, like the website's flares.json.
    """

    __tablename__ = "static_sources"

    latitude_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    longitude_key: Mapped[int] = mapped_column(Integer, primary_key=True)
