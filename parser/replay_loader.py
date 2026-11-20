"""parser/replay_loader.py
========================

Validates file paths and safely opens AoE2 DE recorded game (.aoe2record) binary streams.
Follows strict guard clauses and early returns.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO

from data.exceptions import ReplayLoadError


def validate_replay_path(path: str | Path | None) -> Path:
    """Validate that the provided path points to a readable .aoe2record file.

    Guard Clauses:
        1. Reject None or empty string paths.
        2. Reject paths that do not exist on disk.
        3. Reject directories.
        4. Reject files without the .aoe2record extension (case-insensitive).
        5. Reject 0-byte (empty) files.

    Args:
        path: File path as a string or Path object.

    Returns:
        Path: Resolved, validated Path object.

    Raises:
        ReplayLoadError: If any guard clause check fails.
    """
    # Guard Clause 1: None or empty path
    if path is None:
        raise ReplayLoadError("<empty>", "Replay path cannot be None.")
    str_path = str(path).strip()
    if not str_path:
        raise ReplayLoadError("<empty>", "Replay path cannot be an empty string.")

    target_path = Path(str_path)

    # Guard Clause 2: File existence
    if not target_path.exists():
        raise ReplayLoadError(str(target_path), f"File does not exist: '{target_path}'")

    # Guard Clause 3: Must be a file, not a directory
    if not target_path.is_file():
        raise ReplayLoadError(str(target_path), f"Expected a file, but found a directory: '{target_path}'")

    # Guard Clause 4: Check .aoe2record extension
    if target_path.suffix.lower() != ".aoe2record":
        raise ReplayLoadError(
            str(target_path),
            f"Invalid file extension '{target_path.suffix}'. Only '.aoe2record' files are supported.",
        )

    # Guard Clause 5: File size must be greater than zero
    try:
        file_size = target_path.stat().st_size
    except OSError as e:
        raise ReplayLoadError(str(target_path), f"Failed to check file size: {e}") from e

    if file_size <= 0:
        raise ReplayLoadError(str(target_path), "Replay file is empty (0 bytes).")

    return target_path.resolve()


def open_replay(path: str | Path | None) -> BinaryIO:
    """Validate and open an .aoe2record file as a binary stream.

    Args:
        path: File path as a string or Path object.

    Returns:
        BinaryIO: Open binary file handle.

    Raises:
        ReplayLoadError: If path validation fails or the file cannot be opened.
    """
    validated_path = validate_replay_path(path)
    try:
        return open(validated_path, "rb")
    except (PermissionError, OSError) as e:
        raise ReplayLoadError(
            str(validated_path),
            f"Permission or OS error while opening replay file: {e}",
        ) from e


def list_replays_in_dir(directory: str | Path | None) -> list[Path]:
    """List all .aoe2record files in the given directory (non-recursive).

    Guard Clauses:
        1. Reject None or empty directory path.
        2. Reject non-existent directory.
        3. Reject path if it is not a directory.

    Args:
        directory: Directory path to scan.

    Returns:
        list[Path]: Sorted list of .aoe2record file paths.

    Raises:
        ReplayLoadError: If directory is invalid or not accessible.
    """
    if directory is None:
        raise ReplayLoadError("<empty>", "Directory path cannot be None.")
    str_dir = str(directory).strip()
    if not str_dir:
        raise ReplayLoadError("<empty>", "Directory path cannot be empty.")

    dir_path = Path(str_dir)
    if not dir_path.exists():
        raise ReplayLoadError(str(dir_path), f"Directory does not exist: '{dir_path}'")
    if not dir_path.is_dir():
        raise ReplayLoadError(str(dir_path), f"Path is not a directory: '{dir_path}'")

    try:
        return sorted(p.resolve() for p in dir_path.glob("*.aoe2record") if p.is_file())
    except OSError as e:
        raise ReplayLoadError(str(dir_path), f"Failed to read directory: {e}") from e
