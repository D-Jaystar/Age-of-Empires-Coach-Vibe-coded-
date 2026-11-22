"""analyzer/spatial_heuristics.py
=============================

Calculates spatial and coordinate-based heuristics:
- Euclidean distance calculation between map coordinates
- Town Center proximity micro checks (boar lure / sheep harvesting distance)
- Town Center Gather Point placement (straggler trees vs lumber camp)
- Gaia water object detection (fish, shore fish, deep sea fish)
"""

from __future__ import annotations

import math
from typing import Any


def format_timestamp(seconds: float | None) -> str:
    """Format seconds into a standard MM:SS or HH:MM:SS string.

    Guard Clauses:
        - If seconds is None or negative, returns '00:00'.
    """
    if seconds is None or seconds < 0:
        return "00:00"

    total_sec = int(round(seconds))
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def euclidean_distance(
    x1: float | None,
    y1: float | None,
    x2: float | None,
    y2: float | None,
) -> float:
    """Calculate the 2D Euclidean distance between two coordinate pairs.

    Guard Clauses:
        - If any coordinate is None, returns 0.0.
    """
    if x1 is None or y1 is None or x2 is None or y2 is None:
        return 0.0

    return round(math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2), 2)


def check_gather_distances(
    gather_events: list[dict[str, Any]] | None,
    tc_x: float | None,
    tc_y: float | None,
    boar_threshold: float = 12.0,
    sheep_threshold: float = 5.0,
    deer_threshold: float = 8.0,
    max_time_s: float | None = None,
) -> list[str]:
    """Flag animal harvesting actions taking place far outside the Town Center area.

    In standard AoE2 Dark Age play:
    - Sheep/Cows should be harvested directly under the Town Center (dist <= 5 tiles).
    - Boars should be lured right next to the Town Center (dist <= 6 tiles when harvested).
      Initial lure commands (1-2 villagers clicking a boar > 12 tiles away and bringing it
      to the TC within 75 seconds) are recognized as valid lures, NOT remote harvesting.
    - Deer / Huntables harvested > 8 tiles away without a drop-off point indicate long walking time.

    Guard Clauses:
        - If tc_x or tc_y is None, spatial check cannot be performed; returns empty list.
        - If gather_events is None or empty, returns empty list.

    Returns:
        list[str]: Human-readable diagnostic flags with timestamps and tile distances.
    """
    if tc_x is None or tc_y is None or not gather_events:
        return []

    flags: list[str] = []
    seen_events: set[str] = set()

    for idx, ev in enumerate(gather_events):
        pos_x = ev.get("position_x")
        pos_y = ev.get("position_y")
        if pos_x is None or pos_y is None:
            continue

        param = str(ev.get("param", "")).lower()
        t = float(ev.get("timestamp_s", 0.0))
        if max_time_s is not None and t > max_time_s:
            break
        time_str = format_timestamp(t)
        dist = euclidean_distance(tc_x, tc_y, pos_x, pos_y)
        payload = ev.get("payload", {})
        target_id = payload.get("target_id")
        assigned_vils = len(payload.get("object_ids", []))

        # 1. Check sheep/cow herdable harvesting distance
        if any(animal in param for animal in ("sheep", "cow", "turkey", "pig", "goose")):
            if dist > sheep_threshold:
                # Guard A: During opening seconds (t <= 30s), players shift-click villagers from houses
                # onto sheep while the herdables are still walking towards the Town Center.
                if t <= 30.0:
                    continue

                # Guard B: Check if this herdable was subsequently slaughtered under the TC (<= sheep_threshold) within 120s
                is_slaughtered_under_tc = False
                for future_ev in gather_events[idx + 1:]:
                    future_t = float(future_ev.get("timestamp_s", 0.0))
                    if future_t - t > 120.0:
                        break
                    f_param = str(future_ev.get("param", "")).lower()
                    f_payload = future_ev.get("payload", {})
                    f_target = f_payload.get("target_id")

                    matches_sheep = (target_id is not None and f_target == target_id) or any(
                        animal in f_param for animal in ("sheep", "cow", "turkey", "pig", "goose")
                    )
                    if matches_sheep:
                        f_px = future_ev.get("position_x")
                        f_py = future_ev.get("position_y")
                        if f_px is not None and f_py is not None:
                            if euclidean_distance(tc_x, tc_y, f_px, f_py) <= sheep_threshold:
                                is_slaughtered_under_tc = True
                                break

                if not is_slaughtered_under_tc:
                    flag_key = f"sheep_{int(dist)}_{time_str[:3]}"
                    if flag_key not in seen_events:
                        seen_events.add(flag_key)
                        flags.append(
                            f"Herdable animal harvested {dist:.1f} tiles away from TC at {time_str} (target: <= {sheep_threshold:.0f} tiles under TC)"
                        )

        # 2. Check deer / huntable gathering without drop-off
        elif any(animal in param for animal in ("deer", "ibex", "zebra", "ostrich")):
            if dist > deer_threshold:
                # Check if deer was pushed to TC or subsequently harvested under TC (<= 6.0 tiles) within 240s
                is_pushed_under_tc = False
                for future_ev in gather_events[idx + 1:]:
                    future_t = float(future_ev.get("timestamp_s", 0.0))
                    if future_t - t > 240.0:
                        break
                    f_param = str(future_ev.get("param", "")).lower()
                    f_payload = future_ev.get("payload", {})
                    f_target = f_payload.get("target_id")

                    matches_deer = (target_id is not None and f_target == target_id) or any(
                        animal in f_param for animal in ("deer", "ibex", "zebra", "ostrich")
                    )
                    if matches_deer:
                        f_px = future_ev.get("position_x")
                        f_py = future_ev.get("position_y")
                        if f_px is not None and f_py is not None:
                            if euclidean_distance(tc_x, tc_y, f_px, f_py) <= 6.0:
                                is_pushed_under_tc = True
                                break

                if not is_pushed_under_tc:
                    flag_key = f"deer_{int(dist)}_{time_str[:3]}"
                    if flag_key not in seen_events:
                        seen_events.add(flag_key)
                        flags.append(
                            f"Deer/huntable animal harvested {dist:.1f} tiles away from TC at {time_str} (target: push to TC with scout or build Mill)"
                        )

        # 3. Check boar harvesting distance vs valid boar lure
        elif any(b in param for b in ("boar", "javelina", "rhino", "elephant")):
            if dist > boar_threshold:
                # Distinguish a valid boar lure from harvesting in the wild:
                # Check if the boar was subsequently brought to <= 6.0 tiles of TC within 150s.
                is_valid_lure = False
                for future_ev in gather_events[idx + 1:]:
                    future_t = float(future_ev.get("timestamp_s", 0.0))
                    if future_t - t > 150.0:
                        break
                    f_param = str(future_ev.get("param", "")).lower()
                    f_payload = future_ev.get("payload", {})
                    f_target = f_payload.get("target_id")

                    # Match same boar target or boar param
                    matches_boar = (target_id is not None and f_target == target_id) or any(
                        b in f_param for b in ("boar", "javelina", "rhino", "elephant")
                    )
                    if matches_boar:
                        f_px = future_ev.get("position_x")
                        f_py = future_ev.get("position_y")
                        if f_px is not None and f_py is not None:
                            f_dist = euclidean_distance(tc_x, tc_y, f_px, f_py)
                            if f_dist <= 6.0:
                                is_valid_lure = True
                                break

                if not is_valid_lure:
                    flag_key = f"boar_{int(dist)}_{time_str[:3]}"
                    if flag_key not in seen_events:
                        seen_events.add(flag_key)
                        flags.append(
                            f"Boar harvested {dist:.1f} tiles away from TC at {time_str} (target: lured within {boar_threshold:.0f} tiles of TC)"
                        )

    return flags


def check_tc_gather_point(
    gather_point_events: list[dict[str, Any]] | None,
    tc_x: float | None,
    tc_y: float | None,
    age_start_s: float,
    age_end_s: float,
) -> str | None:
    """Analyze the placement of the Town Center Gather Point during a specific Age.

    Distinguishes whether new villagers are rallied to straggler trees near the TC
    or directly to an external resource (e.g. Lumber Camp or Gold).

    Guard Clauses:
        - If tc_x or tc_y is None, returns None.
        - If gather_point_events is None or empty, returns None.

    Returns:
        str | None: Description of the dominant gather point placement.
    """
    if tc_x is None or tc_y is None or not gather_point_events:
        return None

    distances: list[float] = []

    for ev in gather_point_events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < age_start_s or t > age_end_s:
            continue

        pos_x = ev.get("position_x")
        pos_y = ev.get("position_y")
        if pos_x is not None and pos_y is not None:
            distances.append(euclidean_distance(tc_x, tc_y, pos_x, pos_y))

    if not distances:
        return None

    avg_dist = sum(distances) / len(distances)
    if avg_dist <= 5.0:
        return f"Near TC / Straggler trees (avg distance: {avg_dist:.1f} tiles)"
    if avg_dist <= 18.0:
        return f"Local drop-off camp (avg distance: {avg_dist:.1f} tiles)"
    return f"Forward or distant resource (avg distance: {avg_dist:.1f} tiles)"


def detect_water_map_objects(gaia_objects: list[dict[str, Any]] | None) -> bool:
    """Detect presence of fish or water resources among map gaia objects.

    Guard Clauses:
        - If gaia_objects is None or empty, returns False.

    Returns:
        bool: True if fish or aquatic objects are present on the map.
    """
    if not gaia_objects:
        return False

    fish_keywords = {
        "fish", "shore fish", "great fish", "snapper", "salmon",
        "tuna", "perch", "dorado", "marlin", "box turtle",
    }

    for obj in gaia_objects:
        name = str(obj.get("name", "")).lower()
        if any(kw in name for kw in fish_keywords):
            return True

    return False
