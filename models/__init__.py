# Import every model here so Alembic's autogenerate sees its table.
from models.archive_cell_model import ArchiveCell
from models.archive_grid_cell_model import ArchiveGridCell
from models.base_model import BaseModel
from models.dataset_model import Dataset
from models.fire_detection_model import FireDetection
from models.history_cell_model import HistoryCell
from models.ingestion_run_model import IngestionRun
from models.static_source_model import StaticSource
from models.weather_forecast_model import WeatherForecast

__all__ = [
    "ArchiveCell",
    "ArchiveGridCell",
    "BaseModel",
    "Dataset",
    "FireDetection",
    "HistoryCell",
    "IngestionRun",
    "StaticSource",
    "WeatherForecast",
]
