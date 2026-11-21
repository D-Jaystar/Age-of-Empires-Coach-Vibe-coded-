"""data/exceptions.py - Custom domain exceptions for the AoE Coach pipeline."""

from __future__ import annotations

from typing import Optional


class AoECoachError(Exception):
    """Base exception for all domain errors."""


class ReplayLoadError(AoECoachError):
    """Raised when a replay file cannot be loaded or validated."""
    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to load replay '{path}': {reason}")


class ReplayParseError(AoECoachError):
    """Raised when parsing binary replay content fails."""
    def __init__(
        self,
        path: str,
        reason: str,
        *,
        game_version: Optional[str] = None,
        save_version: Optional[float] = None,
        original_error: Optional[BaseException] = None,
    ) -> None:
        self.path = path
        self.reason = reason
        self.game_version = game_version
        self.save_version = save_version
        self.original_error = original_error
        parts = [f"Failed to parse replay '{path}': {reason}"]
        if game_version:
            parts.append(f"game_version={game_version}")
        if save_version is not None:
            parts.append(f"save_version={save_version}")
        if original_error is not None:
            parts.append(f"original_error={original_error!r}")
        super().__init__(" | ".join(parts))


class UnsupportedPatchError(ReplayParseError):
    """Raised when the replay patch or save version is unsupported."""
    def __init__(self, path: str, patch: str, **kwargs) -> None:
        super().__init__(path, f"Unsupported game patch '{patch}'", **kwargs)
        self.patch = patch


class PlayerNotFoundError(AoECoachError):
    """Raised when a specified player is not present in the replay."""
    def __init__(self, requested: str, available: list[str]) -> None:
        self.requested = requested
        self.available = available
        names = ", ".join(f"'{p}'" for p in available) or "none"
        super().__init__(f"Player '{requested}' not found. Available players: {names}")


class AIAnalysisError(AoECoachError):
    """Raised when AI coaching analysis fails."""


class PayloadTooLargeError(AIAnalysisError):
    """Raised when the telemetry JSON exceeds API size limits."""
