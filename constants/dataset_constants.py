from enum import StrEnum


class DatasetName(StrEnum):
    """Documents in the datasets table, and the website data file each was imported from."""

    ARCHIVE_META = "archive_meta"  # global/meta.json
    ARCHIVE_COUNTRIES = "archive_countries"  # global/countries.json
    ARCHIVE_VALIDATION = "archive_validation"  # global/validation.json
    HISTORY = "history"  # history.json without its cells (those are in history_cells)
    MODEL = "model"  # model/model.json
    MODEL_SAMPLE = "model_sample"  # model/sample.json
    # What the last import stored and when; written on every import, so cached bodies of
    # the cell tables (which have no updated_at) are rebuilt too.
    LAST_IMPORT = "last_import"


# Archive cells (archive_cells) are 0.25°, served in tiles of 40 x 40 cells (10°), like the
# website's former global/tiles/T_<row>_<col>.json files.
ARCHIVE_CELL_DEGREES = 0.25
ARCHIVE_COLS = 1440
ARCHIVE_TILE_CELLS = 40
