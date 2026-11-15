"""Loads the files built by natoor-website/scripts (`npm run data`, `data:global`, `data:model`)
into the database. The directory has the layout those scripts write:

    history.json, flares.json, global/{meta,countries,validation}.json, global/grid.bin,
    global/tiles/T_<row>_<col>.json, model/{model,sample}.json

A missing file is skipped, so one part can be re-imported on its own.
"""

import json
import struct
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from configurations.logger_config import logger
from constants.dataset_constants import DatasetName
from models.archive_cell_model import ArchiveCell
from models.archive_grid_cell_model import ArchiveGridCell
from models.history_cell_model import HistoryCell
from repositories import archive_repository, dataset_repository
from services import static_source_service

DOCUMENTS = {
    DatasetName.ARCHIVE_META: "global/meta.json",
    DatasetName.ARCHIVE_COUNTRIES: "global/countries.json",
    DatasetName.ARCHIVE_VALIDATION: "global/validation.json",
    DatasetName.MODEL: "model/model.json",
    DatasetName.MODEL_SAMPLE: "model/sample.json",
}


def read_json(path: Path):
    return json.loads(path.read_text())


def archive_cell_rows(tiles: Path):
    for tile in sorted(tiles.glob("T_*.json")):
        for row, col, ratio, country, modis, viirs in read_json(tile)["cells"]:
            yield {
                "row": row,
                "col": col,
                "ratio": ratio,
                "country_index": country,
                "modis": modis,
                "viirs": viirs,
            }


def grid_rows(data: bytes):
    count, years = struct.unpack_from("<IH", data)
    cell = struct.Struct(f"<HH{years}H")
    for i in range(count):
        row, col, *yearly = cell.unpack_from(data, 8 + i * cell.size)
        yield {"row": row, "col": col, "yearly": yearly}


def history_rows(cells: list[dict]):
    for c in cells:
        yield {
            "latitude": c["lat"],
            "longitude": c["lon"],
            "country": c["c"],
            "annual": [float(v) for v in c["a"]],  # the file mixes whole and decimal numbers
            "monthly": [float(v) for v in c["m"]],
            "total": c["t"],
        }


def import_directory(session: Session, directory: Path) -> dict[str, int]:
    """Import every file found in `directory`; returns rows stored per dataset or table."""
    stored: dict[str, int] = {}
    for name, relative in DOCUMENTS.items():
        if (path := directory / relative).exists():
            dataset_repository.save(session, name, read_json(path))
            stored[str(name)] = 1
    if (path := directory / "history.json").exists():
        history = read_json(path)
        cells = history.pop("cells")
        dataset_repository.save(session, DatasetName.HISTORY, history)
        stored["history_cells"] = archive_repository.replace(
            session, HistoryCell, history_rows(cells)
        )
    if (tiles := directory / "global/tiles").is_dir():
        stored["archive_cells"] = archive_repository.replace(
            session, ArchiveCell, archive_cell_rows(tiles)
        )
    if (path := directory / "global/grid.bin").exists():
        stored["archive_grid_cells"] = archive_repository.replace(
            session, ArchiveGridCell, grid_rows(path.read_bytes())
        )
    session.commit()
    if (path := directory / "flares.json").exists():
        result = static_source_service.replace_static_sources(session, read_json(path))
        stored["static_sources"] = result["static_sources"]
    dataset_repository.save(
        session,
        DatasetName.LAST_IMPORT,
        {
            "directory": str(directory.resolve()),
            "stored": stored,
            "at": datetime.now(UTC).isoformat(),
        },
    )
    session.commit()
    logger.info("Imported %s from %s", stored, directory)
    return stored
