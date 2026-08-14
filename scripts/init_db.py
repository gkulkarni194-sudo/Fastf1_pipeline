from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _bootstrap import bootstrap_src_layout


bootstrap_src_layout()

from f1_pipeline.db.init_db import init_db


def main() -> None:
    init_db()


if __name__ == "__main__":
    main()
