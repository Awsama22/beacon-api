"""Import the website's built data files into the database.

uv run python -m scripts.import_datasets ../natoor-website/data-build
"""

import sys
from pathlib import Path

from configurations.database_config import get_session_factory
from services.dataset_import_service import import_directory

if __name__ == "__main__":
    directory = Path(sys.argv[1] if len(sys.argv) > 1 else "../natoor-website/data-build")
    if not directory.is_dir():
        sys.exit(f"{directory} is not a directory")
    with get_session_factory()() as session:
        print(import_directory(session, directory))
