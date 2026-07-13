#!/usr/bin/env python3
"""Explicitly build the configured bounded SQLite FTS index."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import SETTINGS
from indexing import ArsenalIndex


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-files", type=int, default=100_000)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()
    if not 1 <= args.max_files <= 1_000_000:
        parser.error("max-files must be between 1 and 1000000")
    if not 1 <= args.timeout_seconds <= 3_600:
        parser.error("timeout-seconds must be between 1 and 3600")
    result = ArsenalIndex(SETTINGS).build(max_files=args.max_files, timeout_seconds=args.timeout_seconds)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
