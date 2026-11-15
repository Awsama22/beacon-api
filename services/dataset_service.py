"""The website's pre-computed data (harmonized archive, GCC history, fire-risk model), read from
the database.

It changes only when the data is re-imported, so each response body is built once and kept until
the next import (the newest datasets.updated_at; every import writes last_import).
"""

import struct

from sqlalchemy.orm import Session

from constants.dataset_constants import (
    ARCHIVE_CELL_DEGREES,
    ARCHIVE_COLS,
    ARCHIVE_TILE_CELLS,
    DatasetName,
)
from repositories import archive_repository, dataset_repository
from utilities.api_error_util import ApiError
from utilities.cached_body_util import CachedBody, VersionedCache, cached_body, cached_json

cache = VersionedCache()


def not_imported(what: str) -> ApiError:
    return ApiError(404, f"{what} is not imported yet (see scripts/import_datasets.py)")


def payload(session: Session, name: DatasetName):
    data = dataset_repository.get_payload(session, name)
    if data is None:
        raise not_imported(f"Dataset {name}")
    return data


def cached(session: Session, key: str, build) -> CachedBody:
    return cache.get(key, dataset_repository.last_updated_at(session), build)


def dataset_body(session: Session, name: DatasetName) -> CachedBody:
    return cached(session, name, lambda: cached_json(payload(session, name)))


def history_body(session: Session) -> CachedBody:
    """history.json: the GCC summary plus every 0.25° cell."""

    def build() -> CachedBody:
        data = payload(session, DatasetName.HISTORY)
        return cached_json({**data, "cells": archive_repository.history_cells(session)})

    return cached(session, "history", build)


def pack_grid(cells) -> bytes:
    """grid.bin: uint32 cell count, uint16 year count, 2 spare bytes, then per cell uint16 row,
    uint16 col and one uint16 per year (all little endian)."""
    parts, years = [], 0
    for row, col, yearly in cells:
        years = len(yearly)
        parts.append(struct.pack(f"<HH{years}H", row, col, *yearly))
    return struct.pack("<IHxx", len(parts), years) + b"".join(parts)


def grid_body(session: Session) -> CachedBody:
    def build() -> CachedBody:
        data = pack_grid(archive_repository.grid_cells(session))
        if struct.unpack_from("<I", data)[0] == 0:  # no cells
            raise not_imported("The archive grid")
        return cached_body(data)

    return cached(session, "grid", build)


def tile_body(session: Session, tile_row: int, tile_col: int) -> CachedBody:
    """One 10° tile, as the former global/tiles/T_<row>_<col>.json:
    {res, cols, cells: [[row, col, ratio, country, modis, viirs], ...]}.
    Empty tiles have no cells."""

    def build() -> CachedBody:
        first_row, first_col = tile_row * ARCHIVE_TILE_CELLS, tile_col * ARCHIVE_TILE_CELLS
        cells = archive_repository.cells_in_range(
            session,
            first_row,
            first_row + ARCHIVE_TILE_CELLS - 1,
            first_col,
            first_col + ARCHIVE_TILE_CELLS - 1,
        )
        return cached_json({"res": ARCHIVE_CELL_DEGREES, "cols": ARCHIVE_COLS, "cells": cells})

    return cached(session, f"tile_{tile_row}_{tile_col}", build)
