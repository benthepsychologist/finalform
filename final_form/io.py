"""Input/output utilities for reading and writing JSONL files."""

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def read_jsonl(path: Path | str) -> Iterator[dict[str, Any]]:
    """Read a JSONL file and yield each record.

    Args:
        path: Path to the JSONL file.

    Yields:
        Each parsed JSON record.
    """
    with open(path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {line_num}: {e}") from e


def write_jsonl(path: Path | str, records: Iterator[dict[str, Any]] | list[dict[str, Any]]) -> int:
    """Write records to a JSONL file.

    Args:
        path: Path to write the JSONL file.
        records: Iterator or list of records to write.

    Returns:
        Number of records written.
    """
    count = 0
    with open(path, "w") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count
