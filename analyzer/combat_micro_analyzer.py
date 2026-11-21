"""analyzer/combat_micro_analyzer.py
==================================

Calculates combat casualties, units lost, and battlefield micro management telemetry:
1. Units Lost & Major Engagements:
   - Ground truth from postgame achievements when available.
   - Deterministic timeseries population drop tracking for casualty spikes and major battles.
2. Battlefield Micro Management:
   - Target / Focus-fire commands (attacking specific units or buildings).
   - Patrol and Attack-Move commands.
   - Stance changes (Stand Ground, Aggressive, Defensive, No Attack).
   - Formation toggles (Line, Staggered, Split).
   - Garrison / Ungarrison micro (dodging raids, preserving low-HP units).
   - Tactical Micro Control Score % (0 - 100%).
"""

from __future__ import annotations

from typing import Any, Optional


def analyze_units_lost(
    player_data: dict[str, Any],
    timeseries: list[Any] | None,
    total_units_trained: int,
    feudal_up_s: float | None = None,
    castle_up_s: float | None = None,
    imp_up_s: float | None = None,
) -> dict[str, Any]:
    """Calculate units lost, casualties per age, and major battle engagement spikes.

    Guard Clauses:
        - Checks for postgame achievements ground-truth first.
        - Falls back to timeseries object drop tracking if achievements are missing.
    """
    # 1. Check ground-truth achievements if available
    achievements = player_data.get("achievements", {})
    mil_achieve = achievements.get("military", {}) if isinstance(achievements, dict) else {}
    exact_lost = mil_achieve.get("units_lost") if isinstance(mil_achieve, dict) else None
    exact_killed = mil_achieve.get("units_killed") if isinstance(mil_achieve, dict) else None

    # 2. Extract casualty drops from timeseries
    drops: list[tuple[float, int]] = []
    total_drop_casualties = 0

    if timeseries and len(timeseries) > 1:
        prev_objects = getattr(timeseries[0], "total_objects", None)
        for row in timeseries[1:]:
            curr_objects = getattr(row, "total_objects", None)
            if prev_objects is not None and curr_objects is not None:
                if curr_objects < prev_objects:
                    diff = prev_objects - curr_objects
                    # Count unit/object drops (filter out 1-unit harvest/sheep decays if needed)
                    ts_raw = getattr(row, "timestamp", None)
                    t_sec = ts_raw.total_seconds() if hasattr(ts_raw, "total_seconds") else float(ts_raw or 0.0)
                    drops.append((t_sec, diff))
                    total_drop_casualties += diff
            if curr_objects is not None:
                prev_objects = curr_objects

    # 3. Calculate calibrated casualties bounded by total units produced
    if exact_lost is not None:
        final_lost = exact_lost
    else:
        # In AoE2 DE, late-game timeseries objects include transient arrows/projectiles.
        # We calibrate battle drop events so casualties remain realistically bounded by total_units_trained.
        raw_battle_losses = sum(d[1] for d in drops if d[1] >= 2)
        if total_units_trained > 0:
            if raw_battle_losses > total_units_trained:
                final_lost = min(total_units_trained, max(1, int(raw_battle_losses * 0.15)))
            else:
                final_lost = raw_battle_losses
        else:
            final_lost = 0

    # 4. Categorize casualties by age
    by_age = {"Dark Age": 0, "Feudal Age": 0, "Castle Age": 0, "Imperial Age": 0}
    major_engagements: list[dict[str, Any]] = []

    f_up = feudal_up_s or float("inf")
    c_up = castle_up_s or float("inf")
    i_up = imp_up_s or float("inf")

    age_weights = {"Dark Age": 0, "Feudal Age": 0, "Castle Age": 0, "Imperial Age": 0}
    for t_sec, count in drops:
        if t_sec < f_up:
            age_weights["Dark Age"] += count
        elif t_sec < c_up:
            age_weights["Feudal Age"] += count
        elif t_sec < i_up:
            age_weights["Castle Age"] += count
        else:
            age_weights["Imperial Age"] += count

        if count >= 6:
            mins = int(t_sec // 60)
            secs = int(t_sec % 60)
            major_engagements.append({
                "timestamp_s": round(t_sec, 1),
                "time_formatted": f"{mins:02d}:{secs:02d}",
                "casualties": count,
            })

    total_weight = sum(age_weights.values()) or 1
    for age_key, w in age_weights.items():
        by_age[age_key] = int(round((w / total_weight) * final_lost))

    # Sort major engagements by casualties descending
    major_engagements.sort(key=lambda x: x["casualties"], reverse=True)

    # Combat preservation efficiency %
    if total_units_trained > 0:
        preservation_pct = round(max(0.0, min(100.0, (1.0 - (final_lost / total_units_trained)) * 100.0)), 1)
    else:
        preservation_pct = 100.0

    return {
        "units_lost": final_lost,
        "units_killed": exact_killed,
        "is_exact_achievement": exact_lost is not None,
        "casualties_by_age": by_age,
        "major_engagements": major_engagements[:5],
        "preservation_efficiency_pct": preservation_pct,
    }


def analyze_micro_actions(
    raw_inputs: list[dict[str, Any]] | None,
    game_duration_s: float = 0.0,
    eapm: int | None = None,
) -> dict[str, Any]:
    """Analyze battlefield micro commands and calculate tactical micro score.

    Guard Clauses:
        - If raw_inputs is None or empty, returns zeroed default metrics.
    """
    if not raw_inputs:
        return {
            "micro_score": 50.0,
            "micro_apm": 0.0,
            "move_commands": 0,
            "target_commands": 0,
            "patrol_commands": 0,
            "garrison_commands": 0,
            "ungarrison_commands": 0,
            "stance_commands": 0,
            "formation_commands": 0,
            "stop_commands": 0,
            "total_tactical_commands": 0,
            "tactical_command_ratio_pct": 0.0,
            "micro_style": "Macro Heavy / Minimal Micro",
        }

    move_count = 0
    target_count = 0
    patrol_count = 0
    garrison_count = 0
    ungarrison_count = 0
    stance_count = 0
    formation_count = 0
    stop_count = 0

    for inp in raw_inputs:
        inp_type = str(inp.get("type", "")).lower()
        if "move" in inp_type:
            move_count += 1
        elif "target" in inp_type:
            target_count += 1
        elif "patrol" in inp_type:
            patrol_count += 1
        elif "ungarrison" in inp_type:
            ungarrison_count += 1
        elif "garrison" in inp_type:
            garrison_count += 1
        elif "stance" in inp_type:
            stance_count += 1
        elif "formation" in inp_type:
            formation_count += 1
        elif "stop" in inp_type:
            stop_count += 1

    tactical_total = (
        move_count + target_count + patrol_count +
        garrison_count + ungarrison_count + stance_count +
        formation_count + stop_count
    )

    total_inputs = len(raw_inputs)
    tactical_ratio = round((tactical_total / total_inputs) * 100.0, 1) if total_inputs > 0 else 0.0

    duration_min = max(1.0, game_duration_s / 60.0)
    micro_apm = round(tactical_total / duration_min, 1)

    # -----------------------------------------------------------------------
    # Micro Score Calculation (0 - 100%)
    # -----------------------------------------------------------------------
    # Component A: Tactical Focus-Fire & Target Control (Weight: 35%)
    if target_count >= 50:
        target_comp = 100.0
    elif target_count >= 25:
        target_comp = 85.0
    elif target_count >= 10:
        target_comp = 70.0
    elif target_count >= 1:
        target_comp = 50.0
    else:
        target_comp = 20.0

    # Component B: Combat Engagement (Patrol, Stance, Formation) (Weight: 35%)
    combat_engagement_actions = patrol_count + stance_count + formation_count + stop_count
    if combat_engagement_actions >= 25:
        engage_comp = 100.0
    elif combat_engagement_actions >= 12:
        engage_comp = 85.0
    elif combat_engagement_actions >= 5:
        engage_comp = 70.0
    elif combat_engagement_actions >= 1:
        engage_comp = 50.0
    else:
        engage_comp = 25.0

    # Component C: Unit Preservation (Garrison / Ungarrison Micro) (Weight: 30%)
    preservation_actions = garrison_count + ungarrison_count
    if preservation_actions >= 20:
        pres_comp = 100.0
    elif preservation_actions >= 8:
        pres_comp = 85.0
    elif preservation_actions >= 2:
        pres_comp = 70.0
    else:
        pres_comp = 40.0

    micro_score = round(
        max(0.0, min(100.0, 0.35 * target_comp + 0.35 * engage_comp + 0.30 * pres_comp)),
        1,
    )

    # Classification
    if micro_score >= 80.0:
        style = "Active Tactical Micro (High Focus Fire & Preservations)"
    elif micro_score >= 60.0:
        style = "Balanced Micro & Attack-Move"
    else:
        style = "Macro-Oriented / Low Unit Micro"

    return {
        "micro_score": micro_score,
        "micro_apm": micro_apm,
        "move_commands": move_count,
        "target_commands": target_count,
        "patrol_commands": patrol_count,
        "garrison_commands": garrison_count,
        "ungarrison_commands": ungarrison_count,
        "stance_commands": stance_count,
        "formation_commands": formation_count,
        "stop_commands": stop_count,
        "total_tactical_commands": tactical_total,
        "tactical_command_ratio_pct": tactical_ratio,
        "micro_style": style,
    }
