"""analyzer/performance_scorer.py
==============================

Calculates high-level executive match performance percentages:
1. Town Center Idle Tracking & TC Uptime % (CaptureAge equivalent benchmark)
2. Economy Efficiency Score % (TC uptime, farm timing/pacing, drop-off walking penalties)
3. Military Value / Focus Score % (Unit composition focus, production volume, blacksmith tech scaling)
"""

from __future__ import annotations

from typing import Any, Optional

from data.models import (
    CastleAgeMetrics,
    DarkAgeMetrics,
    FeudalAgeMetrics,
    ImperialAgeMetrics,
    PerformanceScores,
)


def calculate_performance_scores(
    dark_age: DarkAgeMetrics,
    feudal_age: Optional[FeudalAgeMetrics] = None,
    castle_age: Optional[CastleAgeMetrics] = None,
    imperial_age: Optional[ImperialAgeMetrics] = None,
    game_duration_s: float = 0.0,
) -> PerformanceScores:
    """Calculate deterministic match performance percentage scores.

    Guard Clauses:
        - If dark_age is None, returns 0.0 defaults.
    """
    if not dark_age:
        return PerformanceScores(
            tc_uptime_pct=0.0,
            tc_idle_pct=0.0,
            eco_efficiency_score=0.0,
            military_value_score=0.0,
            total_military_units=0,
        )

    # -----------------------------------------------------------------------
    # 1. TC Idle Tracking & TC Uptime % (Dark Age)
    # -----------------------------------------------------------------------
    ref_time = (
        dark_age.feudal_click_s
        if (dark_age.feudal_click_s is not None and dark_age.feudal_click_s > 0)
        else game_duration_s
    )

    if ref_time > 0:
        tc_idle_pct = round(min(100.0, max(0.0, (dark_age.total_idle_tc_s / ref_time) * 100.0)), 1)
    else:
        tc_idle_pct = 0.0
    tc_uptime_pct = round(max(0.0, 100.0 - tc_idle_pct), 1)

    # -----------------------------------------------------------------------
    # 2. Economy Efficiency Score (0 - 100%)
    # -----------------------------------------------------------------------
    # Component A: TC Uptime (Weight: 45%)
    tc_comp = tc_uptime_pct

    # Component B: Farm Transition & Engine (Weight: 35%)
    if feudal_age and feudal_age.first_farm_time_s:
        farm_t = feudal_age.first_farm_time_s
        if farm_t <= 660.0:  # <= 11:00 min
            farm_comp = 100.0
        elif farm_t <= 840.0:  # <= 14:00 min
            farm_comp = 80.0
        elif farm_t <= 1020.0:  # <= 17:00 min
            farm_comp = 60.0
        else:
            farm_comp = 40.0

        # Bonus for farm build rate (farms/min)
        if feudal_age.farm_build_rate and feudal_age.farm_build_rate >= 2.0:
            farm_comp = min(100.0, farm_comp + 10.0)
    elif feudal_age:
        farm_comp = 40.0
    else:
        # Remained in Dark Age
        farm_comp = 75.0

    # Component C: Drop-off distance & TC Rally Point (Weight: 20%)
    dropoff_comp = 100.0
    if dark_age.tc_distance_flags:
        dropoff_comp -= len(dark_age.tc_distance_flags) * 15.0

    if feudal_age and feudal_age.tc_gather_point_description:
        if "Forward or distant resource" in feudal_age.tc_gather_point_description:
            dropoff_comp -= 20.0

    dropoff_comp = max(20.0, min(100.0, dropoff_comp))

    eco_efficiency = round(
        max(0.0, min(100.0, 0.45 * tc_comp + 0.35 * farm_comp + 0.20 * dropoff_comp)),
        1,
    )

    # -----------------------------------------------------------------------
    # 3. Military Value & Focus Score (0 - 100%)
    # -----------------------------------------------------------------------
    # Count total military units produced
    total_mil_units = 0
    distinct_lines = 1
    focus_factor = 0.8

    if castle_age:
        if castle_age.unit_line_counts:
            total_mil_units += sum(castle_age.unit_line_counts.values())
        distinct_lines = len(castle_age.distinct_unit_lines)
        focus_factor = castle_age.composition_focus_score
    elif feudal_age:
        # Feudal opening military estimate
        if feudal_age.opening_strategy != "none":
            focus_factor = 0.85
            total_mil_units += 4
        else:
            focus_factor = 0.5

    # Component A: Composition Focus (Weight: 50%)
    comp_comp = round(focus_factor * 100.0, 1)

    # Component B: Military Production Volume (Weight: 30%)
    if total_mil_units >= 25:
        volume_comp = 100.0
    elif total_mil_units >= 15:
        volume_comp = 85.0
    elif total_mil_units >= 6:
        volume_comp = 65.0
    elif total_mil_units >= 1:
        volume_comp = 45.0
    else:
        volume_comp = 15.0

    # Component C: Military Tech Scaling (Weight: 20%)
    upgrades_count = 0
    if castle_age and castle_age.blacksmith_upgrades:
        upgrades_count += len(castle_age.blacksmith_upgrades)
    if imperial_age and imperial_age.key_upgrades:
        upgrades_count += len(imperial_age.key_upgrades)

    if upgrades_count >= 4:
        tech_comp = 100.0
    elif upgrades_count >= 2:
        tech_comp = 75.0
    elif upgrades_count >= 1:
        tech_comp = 50.0
    else:
        tech_comp = 20.0

    military_value = round(
        max(0.0, min(100.0, 0.50 * comp_comp + 0.30 * volume_comp + 0.20 * tech_comp)),
        1,
    )

    return PerformanceScores(
        tc_uptime_pct=tc_uptime_pct,
        tc_idle_pct=tc_idle_pct,
        eco_efficiency_score=eco_efficiency,
        military_value_score=military_value,
        total_military_units=total_mil_units,
    )
