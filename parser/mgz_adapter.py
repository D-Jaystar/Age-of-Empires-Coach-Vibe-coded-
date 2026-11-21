"""parser/mgz_adapter.py
======================

Isolates mgz parsing quirks and translates raw binary objects from mgz into
clean, internal data structures and DTOs.
This is the ONLY module in the project that imports or interacts directly with mgz.
"""

from __future__ import annotations

import struct
import zlib
from datetime import timedelta
from typing import Any, BinaryIO

import mgz.model
from config.settings import WATER_MAP_KEYWORDS
from data.exceptions import ReplayParseError, UnsupportedPatchError
from parser.mgz_patch import apply_mgz_patches

# Apply patch for AoE2:DE save versions >= 67.0 / 68.x (build 101.103+)
apply_mgz_patches()


def _safe_duration_seconds(duration: Any) -> float:
    """Extract total seconds safely from a timedelta or numeric duration."""
    if duration is None:
        return 0.0
    if isinstance(duration, timedelta):
        return duration.total_seconds()
    if isinstance(duration, (int, float)):
        return float(duration)
    return 0.0


def extract_match_metadata(match: Any) -> dict[str, Any]:
    """Extract normalized match metadata from an mgz Match instance.

    Guard Clauses:
        - match must not be None.
    """
    if match is None:
        raise ValueError("Match object cannot be None.")

    map_name = getattr(match.map, "name", "Unknown Map") if hasattr(match, "map") and match.map else "Unknown Map"
    map_size = getattr(match.map, "size", "Unknown Size") if hasattr(match, "map") and match.map else "Unknown Size"
    if not map_size:
        map_size = "Unknown"

    game_duration_s = _safe_duration_seconds(getattr(match, "duration", None))

    # Determine winner if available
    winner_name: str | None = None
    if hasattr(match, "players") and match.players:
        winners = [p.name for p in match.players if getattr(p, "winner", None) is True]
        if winners:
            winner_name = ", ".join(winners)

    # Classify water / hybrid maps based on name keywords
    lower_map = map_name.lower()
    is_water = any(kw in lower_map for kw in WATER_MAP_KEYWORDS)
    hybrid_keywords = {"four lakes", "baltic", "cross", "mediterranean", "coastal", "continental", "rivers", "bog"}
    is_hybrid = any(kw in lower_map for kw in hybrid_keywords)

    game_version = str(getattr(match, "game_version", "Unknown"))
    save_version_raw = getattr(match, "save_version", 0.0)
    try:
        save_version = float(save_version_raw) if save_version_raw is not None else 0.0
    except (ValueError, TypeError):
        save_version = 0.0

    raw_type = getattr(match, "type", "Random Map")
    gamemode_name = str(raw_type) if raw_type else "Random Map"
    diplomacy_type = str(getattr(match, "diplomacy_type", "")) or None

    return {
        "map_name": map_name,
        "map_size": str(map_size),
        "game_duration_s": game_duration_s,
        "winner_name": winner_name,
        "is_water_map": is_water,
        "is_hybrid_map": is_hybrid,
        "game_version": game_version,
        "save_version": save_version,
        "gamemode": gamemode_name,
        "diplomacy": diplomacy_type,
    }


def extract_player_data(match: Any) -> list[dict[str, Any]]:
    """Extract player information and their starting TC coordinates.

    Guard Clauses:
        - match must not be None.
    """
    if match is None:
        raise ValueError("Match object cannot be None.")
    if not hasattr(match, "players") or not match.players:
        return []

    players_data: list[dict[str, Any]] = []
    for player in match.players:
        # Resolve TC coordinates
        tc_x: float | None = None
        tc_y: float | None = None
        if hasattr(player, "position") and player.position is not None:
            tc_x = getattr(player.position, "x", None)
            tc_y = getattr(player.position, "y", None)

        # Fallback: scan starting objects for Town Center (TC IDs: 71, 109, 141, 142)
        if tc_x is None and hasattr(player, "objects") and player.objects:
            tc_ids = {71, 109, 141, 142}
            for obj in player.objects:
                obj_id = getattr(obj, "object_id", None)
                if obj_id in tc_ids and hasattr(obj, "position") and obj.position:
                    tc_x = getattr(obj.position, "x", None)
                    tc_y = getattr(obj.position, "y", None)
                    break

        eapm = getattr(player, "eapm", None)
        winner = getattr(player, "winner", None)
        profile_id = getattr(player, "profile_id", None)

        players_data.append({
            "number": player.number,
            "name": player.name,
            "civilization": getattr(player, "civilization", "Unknown"),
            "color": getattr(player, "color", "Unknown"),
            "tc_x": float(tc_x) if tc_x is not None else None,
            "tc_y": float(tc_y) if tc_y is not None else None,
            "eapm": int(eapm) if eapm is not None else None,
            "winner": winner,
            "profile_id": int(profile_id) if profile_id is not None else None,
        })

    return players_data


def extract_player_inputs(match: Any, player_number: int) -> list[dict[str, Any]]:
    """Filter and normalize inputs for a specific player.

    Guard Clauses:
        - match must not be None.
        - player_number must be an integer.
    """
    if match is None:
        raise ValueError("Match object cannot be None.")
    if not isinstance(player_number, int):
        raise ValueError("player_number must be an integer.")

    if not hasattr(match, "inputs") or not match.inputs:
        return []

    normalized_inputs: list[dict[str, Any]] = []
    for inp in match.inputs:
        if not hasattr(inp, "player") or inp.player is None:
            continue
        if getattr(inp.player, "number", None) != player_number:
            continue

        timestamp_s = _safe_duration_seconds(getattr(inp, "timestamp", None))
        inp_type = str(getattr(inp, "type", "Unknown"))
        param = getattr(inp, "param", None)
        param_str = str(param) if param is not None else None

        pos_x: float | None = None
        pos_y: float | None = None
        if hasattr(inp, "position") and inp.position is not None:
            pos_x = getattr(inp.position, "x", None)
            pos_y = getattr(inp.position, "y", None)

        payload = getattr(inp, "payload", {})
        if not isinstance(payload, dict):
            payload = {}

        normalized_inputs.append({
            "timestamp_s": timestamp_s,
            "type": inp_type,
            "param": param_str,
            "position_x": float(pos_x) if pos_x is not None else None,
            "position_y": float(pos_y) if pos_y is not None else None,
            "payload": payload,
        })

    # Sort deterministically by timestamp
    normalized_inputs.sort(key=lambda x: x["timestamp_s"])
    return normalized_inputs


def extract_player_actions(match: Any, player_number: int) -> list[dict[str, Any]]:
    """Filter and normalize raw actions for a specific player."""
    if match is None:
        raise ValueError("Match object cannot be None.")
    if not hasattr(match, "actions") or not match.actions:
        return []

    normalized_actions: list[dict[str, Any]] = []
    for act in match.actions:
        if not hasattr(act, "player") or act.player is None:
            continue
        if getattr(act.player, "number", None) != player_number:
            continue

        timestamp_s = _safe_duration_seconds(getattr(act, "timestamp", None))
        act_type = getattr(act.type, "name", str(act.type))

        pos_x: float | None = None
        pos_y: float | None = None
        if hasattr(act, "position") and act.position is not None:
            pos_x = getattr(act.position, "x", None)
            pos_y = getattr(act.position, "y", None)

        payload = getattr(act, "payload", {})
        if not isinstance(payload, dict):
            payload = {}

        normalized_actions.append({
            "timestamp_s": timestamp_s,
            "type": act_type,
            "position_x": float(pos_x) if pos_x is not None else None,
            "position_y": float(pos_y) if pos_y is not None else None,
            "payload": payload,
        })

    normalized_actions.sort(key=lambda x: x["timestamp_s"])
    return normalized_actions


def extract_uptimes(match: Any) -> dict[int, dict[str, float]]:
    """Group uptimes by player number.

    Returns:
        dict[player_number, {'feudal': seconds, 'castle': seconds, 'imperial': seconds}]
    """
    if match is None:
        raise ValueError("Match object cannot be None.")
    if not hasattr(match, "uptimes") or not match.uptimes:
        return {}

    uptimes_by_player: dict[int, dict[str, float]] = {}
    for up in match.uptimes:
        if not hasattr(up, "player") or up.player is None:
            continue
        p_num = getattr(up.player, "number", None)
        if p_num is None:
            continue

        if p_num not in uptimes_by_player:
            uptimes_by_player[p_num] = {}

        timestamp_s = _safe_duration_seconds(getattr(up, "timestamp", None))
        age_enum = getattr(up, "age", None)
        age_name = getattr(age_enum, "name", str(age_enum)).lower()

        if "feudal" in age_name:
            uptimes_by_player[p_num]["feudal"] = timestamp_s
        elif "castle" in age_name:
            uptimes_by_player[p_num]["castle"] = timestamp_s
        elif "imperial" in age_name:
            uptimes_by_player[p_num]["imperial"] = timestamp_s

    return uptimes_by_player


def extract_gaia_objects(match: Any) -> list[dict[str, Any]]:
    """Extract gaia objects (resources, animals, relics) from the map."""
    if match is None:
        raise ValueError("Match object cannot be None.")
    if not hasattr(match, "gaia") or not match.gaia:
        return []

    gaia_list: list[dict[str, Any]] = []
    for obj in match.gaia:
        pos_x: float | None = None
        pos_y: float | None = None
        if hasattr(obj, "position") and obj.position is not None:
            pos_x = getattr(obj.position, "x", None)
            pos_y = getattr(obj.position, "y", None)

        gaia_list.append({
            "name": getattr(obj, "name", "Unknown"),
            "object_id": getattr(obj, "object_id", 0),
            "class_id": getattr(obj, "class_id", 0),
            "instance_id": getattr(obj, "instance_id", 0),
            "x": float(pos_x) if pos_x is not None else None,
            "y": float(pos_y) if pos_y is not None else None,
        })
    return gaia_list


def parse_replay(handle: BinaryIO, replay_path: str = "stream") -> dict[str, Any]:
    """Parse an open recorded game binary stream using mgz.model.parse_match.

    Wraps third-party mgz exceptions and produces clean, domain-specific exceptions.

    Guard Clauses:
        - handle must not be None.

    Args:
        handle: Binary stream positioned at byte 0.
        replay_path: Human-readable path or identifier for error reporting.

    Returns:
        dict: Normalized structure containing metadata, players, uptimes, and gaia objects.

    Raises:
        UnsupportedPatchError: When the replay format or patch version is unsupported.
        ReplayParseError: When parsing fails due to data corruption, EOF, or struct errors.
    """
    if handle is None:
        raise ValueError("Binary stream handle cannot be None.")

    try:
        match = mgz.model.parse_match(handle)
    except (struct.error, zlib.error, EOFError, MemoryError, AssertionError, ValueError, RuntimeError) as e:
        err_msg = str(e)
        if "not supported" in err_msg.lower():
            raise UnsupportedPatchError(replay_path, patch=err_msg, original_error=e) from e
        raise ReplayParseError(replay_path, reason=f"mgz parser error: {err_msg}", original_error=e) from e
    except Exception as e:
        raise ReplayParseError(replay_path, reason=f"Unexpected parser failure: {e}", original_error=e) from e

    metadata = extract_match_metadata(match)
    players = extract_player_data(match)
    uptimes = extract_uptimes(match)
    gaia = extract_gaia_objects(match)

    return {
        "match": match,
        "metadata": metadata,
        "players": players,
        "uptimes": uptimes,
        "gaia": gaia,
    }
