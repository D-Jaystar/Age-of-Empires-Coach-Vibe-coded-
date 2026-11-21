"""parser/replay_loader.py - Validates and opens .aoe2record binary streams."""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

from data.exceptions import ReplayLoadError


def validate_replay_path(path: str | Path | None) -> Path:
    """Validate that path points to an existing, non-empty .aoe2record file."""
    if path is None:
        raise ReplayLoadError("<empty>", "Replay path cannot be None.")
    str_path = str(path).strip()
    if not str_path:
        raise ReplayLoadError("<empty>", "Replay path cannot be an empty string.")

    target = Path(str_path)

    if not target.exists():
        raise ReplayLoadError(str(target), f"File does not exist: '{target}'")
    if not target.is_file():
        raise ReplayLoadError(str(target), f"Expected a file, but found a directory: '{target}'")
    if target.suffix.lower() != ".aoe2record":
        raise ReplayLoadError(str(target), f"Invalid file extension '{target.suffix}'. Only '.aoe2record' files are supported.")

    try:
        if target.stat().st_size <= 0:
            raise ReplayLoadError(str(target), "Replay file is empty (0 bytes).")
    except OSError as e:
        raise ReplayLoadError(str(target), f"Failed to check file size: {e}") from e

    return target.resolve()


def open_replay(path: str | Path | None) -> BinaryIO:
    """Validate and open an .aoe2record file as a binary stream."""
    target = validate_replay_path(path)
    try:
        return open(target, "rb")
    except (PermissionError, OSError) as e:
        raise ReplayLoadError(str(target), f"Permission or OS error while opening file: {e}") from e
