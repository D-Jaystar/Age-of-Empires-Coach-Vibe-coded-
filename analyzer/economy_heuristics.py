"""analyzer/economy_heuristics.py
==============================

Calculates concrete economic signals, benchmarks, and efficiency heuristics
from parsed replay events:
- Idle TC estimator and queue gap cross-referencing (e.g. boar lure panic)
- Feudal click villager count estimation
- Loom timing classification (early vs late)
- Dark Age resource gather distribution proxy
- Feudal farm timing, count, and build rate
- Wheelbarrow timing and villager population proxy
- First 25 actions build-order extraction
"""

from __future__ import annotations

from typing import Any

from config.settings import AoE2Constants
from data.models import BuildOrderEntry, IdleTCGap


def calculate_idle_tc_gaps(
    events: list[dict[str, Any]] | None,
    feudal_click_s: float | None,
    game_duration_s: float,
    threshold_s: float = 30.0,
) -> tuple[list[IdleTCGap], float]:
    """Calculate Town Center idle gaps and total idle time during the Dark Age.

    Models the Town Center queue timeline: each villager takes 25s, Loom takes 25s.
    If a gap between TC tasks exceeds `threshold_s`, it is flagged as an IdleTCGap.
    Any gap occurring within ±20s of a Boar gather command is cross-referenced
    with the context "near boar lure".

    Guard Clauses:
        - If game_duration_s <= 0, returns ([], 0.0).
        - If events is empty/None, calculates idle time from t=0 to cutoff.

    Args:
        events: Chronologically sorted player events.
        feudal_click_s: Timestamp of Feudal Age research start (or None).
        game_duration_s: Total match duration in seconds.
        threshold_s: Minimum idle duration in seconds to report as a gap.

    Returns:
        tuple[list[IdleTCGap], float]: List of flagged gaps and total accumulated idle seconds.
    """
    cutoff_s = feudal_click_s if feudal_click_s is not None else game_duration_s
    cutoff_s = max(0.0, min(cutoff_s, game_duration_s))

    if cutoff_s <= 0.0:
        return [], 0.0

    if not events:
        total_idle = round(cutoff_s, 1)
        if total_idle >= threshold_s:
            gap = IdleTCGap(
                start_s=0.0,
                end_s=cutoff_s,
                duration_s=total_idle,
                context="no TC production recorded",
            )
            return [gap], total_idle
        return [], total_idle

    # Extract all Boar interaction timestamps for context cross-referencing
    boar_timestamps: list[float] = []
    for ev in events:
        if ev.get("timestamp_s", 0.0) > cutoff_s:
            break
        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()
        if "boar" in param or ("gather" in inp_type and "boar" in str(ev.get("payload", "")).lower()):
            boar_timestamps.append(float(ev.get("timestamp_s", 0.0)))

    # Collect TC-occupying tasks: Villager queue and Loom research
    tc_tasks: list[tuple[float, float]] = []  # (event_time, task_duration)
    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t > cutoff_s:
            break

        inp_type = str(ev.get("type", "")).lower()
        param = str(ev.get("param", "")).lower()

        # Check for Villager production
        if "villager" in param or ("queue" in inp_type and "villager" in param):
            tc_tasks.append((t, float(AoE2Constants.VILLAGER_TRAIN_TIME_S)))
        # Check for Loom research
        elif "loom" in param or ("research" in inp_type and "loom" in param):
            tc_tasks.append((t, float(AoE2Constants.LOOM_RESEARCH_TIME_S)))

    gaps: list[IdleTCGap] = []
    total_idle_time = 0.0
    tc_free_time = 0.0

    for queue_time, duration in tc_tasks:
        if queue_time > tc_free_time:
            gap_duration = queue_time - tc_free_time
            total_idle_time += gap_duration

            if gap_duration >= threshold_s:
                # Check for nearby boar lure
                near_boar = any(abs(b - queue_time) <= 20.0 or abs(b - tc_free_time) <= 20.0 for b in boar_timestamps)
                ctx = "near boar lure" if near_boar else None

                gaps.append(
                    IdleTCGap(
                        start_s=round(tc_free_time, 1),
                        end_s=round(queue_time, 1),
                        duration_s=round(gap_duration, 1),
                        context=ctx,
                    )
                )
            tc_free_time = queue_time + duration
        else:
            # TC was already busy; task queues back-to-back
            tc_free_time += duration

    # Final gap between last task completion and Feudal click / cutoff
    if cutoff_s > tc_free_time:
        gap_duration = cutoff_s - tc_free_time
        total_idle_time += gap_duration
        if gap_duration >= threshold_s:
            near_boar = any(abs(b - tc_free_time) <= 20.0 for b in boar_timestamps)
            ctx = "near boar lure" if near_boar else None
            gaps.append(
                IdleTCGap(
                    start_s=round(tc_free_time, 1),
                    end_s=round(cutoff_s, 1),
                    duration_s=round(gap_duration, 1),
                    context=ctx,
                )
            )

    return gaps, round(total_idle_time, 1)


def estimate_vils_at_feudal_click(
    events: list[dict[str, Any]] | None,
    feudal_click_s: float | None,
) -> int | None:
    """Estimate total villager population at the moment of Feudal Age research click.

    Guard Clauses:
        - If feudal_click_s is None, returns None.
        - If events is empty/None, returns base starting villagers (3).

    Args:
        events: List of player events.
        feudal_click_s: Timestamp of Feudal Age click.

    Returns:
        int | None: Estimated villager count, or None if Feudal was never clicked.
    """
    if feudal_click_s is None:
        return None
    if not events:
        return 3

    vils_trained = 0
    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t >= feudal_click_s:
            break
        param = str(ev.get("param", "")).lower()
        if "villager" in param:
            vils_trained += 1

    return 3 + vils_trained


def detect_loom_timing(
    events: list[dict[str, Any]] | None,
    feudal_click_s: float | None,
) -> tuple[float | None, bool | None]:
    """Detect Loom research timestamp and classify if it was researched unusually early.

    Early Loom heuristic: researched before 180s (3 minutes) or with fewer than 15 vils,
    long before clicking Feudal Age.

    Guard Clauses:
        - If events is None or empty, returns (None, None).

    Returns:
        tuple[float | None, bool | None]: (loom_time_s, loom_early_flag).
    """
    if not events:
        return None, None

    loom_time: float | None = None
    vils_before_loom = 0

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "villager" in param:
            vils_before_loom += 1

        if "loom" in param or ("research" in inp_type and "loom" in param):
            loom_time = t
            break

    if loom_time is None:
        return None, None

    # Classify early loom: researched before 3:00 (180s) or with <= 12 vils trained
    is_early = False
    if loom_time < 180.0 or vils_before_loom <= 12:
        if feudal_click_s is not None and (feudal_click_s - loom_time) > 120.0:
            is_early = True
        elif feudal_click_s is None and loom_time < 200.0:
            is_early = True

    return round(loom_time, 1), is_early


def calculate_resource_gather_ratios(
    events: list[dict[str, Any]] | None,
    start_s: float = 0.0,
    end_s: float = float("inf"),
) -> dict[str, float]:
    """Estimate resource focus ratios (wood, food, gold, stone) in a time window.

    Uses gather commands, drop-off building construction (Mill, Lumber Camp, Mining Camp),
    and Farm seeding as proxy signals.

    Guard Clauses:
        - If events is None or empty, returns balanced default ratios.
        - Guard against division by zero.

    Returns:
        dict[str, float]: Proportions summing to 1.0 (e.g. {'food': 0.60, 'wood': 0.30, ...}).
    """
    default_ratios = {"food": 0.55, "wood": 0.35, "gold": 0.05, "stone": 0.05}
    if not events:
        return default_ratios

    counts = {"food": 0, "wood": 0, "gold": 0, "stone": 0}
    food_keywords = {"sheep", "boar", "deer", "forage", "berry", "farm", "mill", "cow", "turkey", "goose", "pig", "fish"}
    wood_keywords = {"tree", "wood", "lumber camp", "forest"}
    gold_keywords = {"gold", "mining camp"}
    stone_keywords = {"stone"}

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < start_s:
            continue
        if t > end_s:
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()
        payload = ev.get("payload", {})
        assigned_vils = len(payload.get("object_ids", [])) if payload.get("object_ids") else 1

        if any(kw in param for kw in food_keywords) or "reseed" in inp_type:
            counts["food"] += assigned_vils
        elif any(kw in param for kw in wood_keywords):
            counts["wood"] += assigned_vils
        elif any(kw in param for kw in gold_keywords):
            counts["gold"] += assigned_vils
        elif any(kw in param for kw in stone_keywords):
            counts["stone"] += assigned_vils

    total = sum(counts.values())
    if total == 0:
        return default_ratios

    return {
        "food": round(counts["food"] / total, 2),
        "wood": round(counts["wood"] / total, 2),
        "gold": round(counts["gold"] / total, 2),
        "stone": round(counts["stone"] / total, 2),
    }


def detect_farm_timing(
    events: list[dict[str, Any]] | None,
    start_s: float,
    end_s: float,
) -> tuple[float | None, int, float | None]:
    """Detect first Farm build timestamp, total farms built, and farm build rate per minute.

    Guard Clauses:
        - If events is None or empty, returns (None, 0, 0.0).
        - If duration <= 0, returns build rate 0.0 to prevent division by zero.

    Returns:
        tuple[first_farm_s, total_farms, farms_per_minute].
    """
    if not events:
        return None, 0, 0.0

    duration_min = max(0.0, (end_s - start_s) / 60.0)
    first_farm: float | None = None
    farm_count = 0

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < start_s:
            continue
        if t > end_s:
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "farm" in param or "reseed" in inp_type:
            farm_count += 1
            if first_farm is None:
                first_farm = t

    build_rate = round(farm_count / duration_min, 2) if duration_min > 0.0 else 0.0
    return (round(first_farm, 1) if first_farm is not None else None, farm_count, build_rate)


def detect_wheelbarrow_timing(
    events: list[dict[str, Any]] | None,
) -> tuple[float | None, int | None]:
    """Detect Wheelbarrow research timestamp and estimated villager count when researched.

    Guard Clauses:
        - If events is None or empty, returns (None, None).

    Returns:
        tuple[wheelbarrow_time_s, vil_count_at_research].
    """
    if not events:
        return None, None

    wb_time: float | None = None
    vils_before_wb = 3

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "villager" in param:
            vils_before_wb += 1

        if "wheelbarrow" in param or ("research" in inp_type and "wheelbarrow" in param):
            wb_time = t
            break

    if wb_time is None:
        return None, None

    return round(wb_time, 1), vils_before_wb


def extract_build_order(
    events: list[dict[str, Any]] | None,
    max_entries: int = 25,
) -> list[BuildOrderEntry]:
    """Extract the first chronological build-order actions (buildings, techs, military units).

    Excludes routine villager queues to keep the build order concise and readable.

    Guard Clauses:
        - If events is None or empty, returns empty list.
        - max_entries must be > 0.
    """
    if not events or max_entries <= 0:
        return []

    entries: list[BuildOrderEntry] = []
    for ev in events:
        if len(entries) >= max_entries:
            break

        inp_type = str(ev.get("type", ""))
        param = ev.get("param")
        param_str = str(param) if param is not None else ""

        # Filter for meaningful build-order events
        is_build = "build" in inp_type.lower()
        is_research = "research" in inp_type.lower()
        is_special_queue = "queue" in inp_type.lower() and "villager" not in param_str.lower()

        if is_build or is_research or is_special_queue:
            entries.append(
                BuildOrderEntry(
                    timestamp_s=round(float(ev.get("timestamp_s", 0.0)), 1),
                    action_type=inp_type,
                    param=param_str if param_str else None,
                    position_x=ev.get("position_x"),
                    position_y=ev.get("position_y"),
                )
            )

    return entries
