"""Custom domain exceptions for the AoE Coach application.

All exceptions inherit from :class:`AoECoachError` so callers can catch
the entire family with a single ``except AoECoachError`` clause.
"""

from __future__ import annotations

from typing import List, Optional


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class AoECoachError(Exception):
    """Base exception for every error raised by the AoE Coach domain layer."""


# ---------------------------------------------------------------------------
# Replay I/O
# ---------------------------------------------------------------------------

class ReplayLoadError(AoECoachError):
    """Raised when a replay file cannot be loaded.

    Covers missing files, wrong extensions, empty files, and permission errors.
    """

    def __init__(self, path: str, reason: str) -> None:
        if not path:
            raise ValueError("ReplayLoadError requires a non-empty 'path'.")
        if not reason:
            raise ValueError("ReplayLoadError requires a non-empty 'reason'.")

        self.path = path
        self.reason = reason
        super().__init__(str(self))

    def __str__(self) -> str:
        return f"Failed to load replay '{self.path}': {self.reason}"


# ---------------------------------------------------------------------------
# Replay parsing
# ---------------------------------------------------------------------------

class ReplayParseError(AoECoachError):
    """Raised when *mgz* fails to parse the binary replay content.

    Typical causes: struct-unpacking errors, truncated data, or corrupt files.
    """

    def __init__(
        self,
        path: str,
        reason: str,
        *,
        game_version: Optional[str] = None,
        save_version: Optional[float] = None,
        original_error: Optional[BaseException] = None,
    ) -> None:
        if not path:
            raise ValueError("ReplayParseError requires a non-empty 'path'.")
        if not reason:
            raise ValueError("ReplayParseError requires a non-empty 'reason'.")

        self.path = path
        self.reason = reason
        self.game_version = game_version
        self.save_version = save_version
        self.original_error = original_error
        super().__init__(str(self))

    def __str__(self) -> str:
        parts = [f"Failed to parse replay '{self.path}': {self.reason}"]
        if self.game_version is not None:
            parts.append(f"game_version={self.game_version}")
        if self.save_version is not None:
            parts.append(f"save_version={self.save_version}")
        if self.original_error is not None:
            parts.append(f"original_error={self.original_error!r}")
        return " | ".join(parts)


class UnsupportedPatchError(ReplayParseError):
    """Raised when *mgz* cannot handle a specific game patch or version.

    This is a specialisation of :class:`ReplayParseError` for cases where the
    replay itself is valid but the parser lacks support for that patch.
    """

    def __init__(
        self,
        path: str,
        patch: str,
        *,
        game_version: Optional[str] = None,
        save_version: Optional[float] = None,
        original_error: Optional[BaseException] = None,
    ) -> None:
        if not patch:
            raise ValueError("UnsupportedPatchError requires a non-empty 'patch'.")

        self.patch = patch
        reason = f"Unsupported game patch: {patch}"
        super().__init__(
            path,
            reason,
            game_version=game_version,
            save_version=save_version,
            original_error=original_error,
        )

    def __str__(self) -> str:
        parts = [f"Unsupported patch '{self.patch}' in replay '{self.path}'"]
        if self.game_version is not None:
            parts.append(f"game_version={self.game_version}")
        if self.save_version is not None:
            parts.append(f"save_version={self.save_version}")
        if self.original_error is not None:
            parts.append(f"original_error={self.original_error!r}")
        return " | ".join(parts)


# ---------------------------------------------------------------------------
# Player lookup
# ---------------------------------------------------------------------------

class PlayerNotFoundError(AoECoachError):
    """Raised when the requested player name is not found in the replay.

    The *available_players* list lets callers surface useful "did you mean?"
    diagnostics.
    """

    def __init__(self, player_name: str, available_players: List[str]) -> None:
        if not player_name:
            raise ValueError("PlayerNotFoundError requires a non-empty 'player_name'.")
        if available_players is None:
            raise ValueError("PlayerNotFoundError requires an 'available_players' list.")

        self.player_name = player_name
        self.available_players = available_players
        super().__init__(str(self))

    def __str__(self) -> str:
        players = ", ".join(self.available_players) if self.available_players else "(none)"
        return (
            f"Player '{self.player_name}' not found. "
            f"Available players: [{players}]"
        )


# ---------------------------------------------------------------------------
# AI / LLM interaction
# ---------------------------------------------------------------------------

class AIAnalysisError(AoECoachError):
    """Raised when the LLM API call fails.

    Covers network errors, authentication failures, rate-limiting, and
    response-parsing problems.
    """

    def __init__(
        self,
        reason: str,
        *,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
    ) -> None:
        if not reason:
            raise ValueError("AIAnalysisError requires a non-empty 'reason'.")

        self.reason = reason
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(str(self))

    def __str__(self) -> str:
        parts = [f"AI analysis failed: {self.reason}"]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        if self.retry_after is not None:
            parts.append(f"retry_after={self.retry_after}s")
        return " | ".join(parts)


class PayloadTooLargeError(AoECoachError):
    """Raised when the JSON payload exceeds the LLM context-window limit."""

    def __init__(self, payload_size: int, max_size: int) -> None:
        if payload_size is None or payload_size < 0:
            raise ValueError("PayloadTooLargeError requires a non-negative 'payload_size'.")
        if max_size is None or max_size < 0:
            raise ValueError("PayloadTooLargeError requires a non-negative 'max_size'.")

        self.payload_size = payload_size
        self.max_size = max_size
        super().__init__(str(self))

    def __str__(self) -> str:
        return (
            f"Payload too large for LLM context: "
            f"{self.payload_size:,} bytes exceeds limit of {self.max_size:,} bytes"
        )
