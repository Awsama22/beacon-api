from collections.abc import Iterable, Iterator

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from models.archive_cell_model import ArchiveCell
from models.archive_grid_cell_model import ArchiveGridCell
from models.history_cell_model import HistoryCell


def cells_in_range(
    session: Session, first_row: int, last_row: int, first_col: int, last_col: int
) -> list[list]:
    """Archive cells as tile rows: [row, col, ratio, country, modis, viirs]."""
    query = select(
        ArchiveCell.row,
        ArchiveCell.col,
        ArchiveCell.ratio,
        ArchiveCell.country_index,
        ArchiveCell.modis,
        ArchiveCell.viirs,
    ).where(
        ArchiveCell.row.between(first_row, last_row), ArchiveCell.col.between(first_col, last_col)
    )
    return [list(row) for row in session.execute(query)]


def grid_cells(session: Session) -> Iterator[tuple[int, int, list[int]]]:
    query = select(ArchiveGridCell.row, ArchiveGridCell.col, ArchiveGridCell.yearly).order_by(
        ArchiveGridCell.row, ArchiveGridCell.col
    )
    return session.execute(query.execution_options(yield_per=20000)).tuples()


def history_cells(session: Session) -> list[dict]:
    """GCC history cells in history.json's shape, largest total first."""
    query = select(HistoryCell).order_by(HistoryCell.total.desc())
    return [
        {
            "lat": c.latitude,
            "lon": c.longitude,
            "c": c.country,
            "a": c.annual,
            "m": c.monthly,
            "t": c.total,
        }
        for c in session.scalars(query)
    ]


def replace(session: Session, model: type, rows: Iterable[dict]) -> int:
    """Replace every row of an archive table (archive_cells, archive_grid_cells, history_cells)."""
    rows = list(rows)
    session.execute(delete(model))
    if rows:
        session.execute(insert(model), rows)
    return len(rows)
