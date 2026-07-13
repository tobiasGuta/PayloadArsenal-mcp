#!/usr/bin/env python3
"""Report safe metadata for the configured SQLite FTS index."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import SETTINGS
from indexing import ArsenalIndex


def main() -> int:
    status = ArsenalIndex(SETTINGS).status()
    print(json.dumps(status, sort_keys=True))
    return 0 if status["available"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
