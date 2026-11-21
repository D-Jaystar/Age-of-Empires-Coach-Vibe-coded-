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
    units_lost: Optional[int] = None,
    micro_score: Optional[float] = None,
    micro_apm: Optional[float] = None,
    micro_style: Optional[str] = None,
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
    # 3. Multi-Layer Military Value & Focus Score (0 - 100%)
    # -----------------------------------------------------------------------
    # Layer 1: Aggregate unit counts across all game ages
    military_by_age: dict[str, int] = {}
    all_unit_lines: dict[str, int] = {}

    feud_units = 0
    if feudal_age:
        feud_units = feudal_age.military_units_trained or sum(feudal_age.unit_line_counts.values())
        if feud_units > 0:
            military_by_age["Feudal Age"] = feud_units
        for line, cnt in feudal_age.unit_line_counts.items():
            all_unit_lines[line] = all_unit_lines.get(line, 0) + cnt

    castle_units = 0
    if castle_age:
        castle_units = castle_age.military_units_trained or sum(castle_age.unit_line_counts.values())
        if castle_units > 0:
            military_by_age["Castle Age"] = castle_units
        for line, cnt in castle_age.unit_line_counts.items():
            all_unit_lines[line] = all_unit_lines.get(line, 0) + cnt

    imp_units = 0
    if imperial_age:
        imp_units = imperial_age.military_units_trained or sum(imperial_age.unit_line_counts.values())
        if imp_units > 0:
            military_by_age["Imperial Age"] = imp_units
        for line, cnt in imperial_age.unit_line_counts.items():
            all_unit_lines[line] = all_unit_lines.get(line, 0) + cnt

    total_mil_units = feud_units + castle_units + imp_units
    top_military_lines = dict(sorted(all_unit_lines.items(), key=lambda x: x[1], reverse=True))

    # Layer 2: Composition Focus Evaluation
    if castle_age:
        focus_factor = castle_age.composition_focus_score
    elif feudal_age:
        focus_factor = 0.85 if feudal_age.opening_strategy != "none" else 0.5
    else:
        focus_factor = 0.5

    comp_comp = round(focus_factor * 100.0, 1)

    # Layer 3: Military Production Volume & Pace (relative to match duration)
    post_dark_start = (
        dark_age.feudal_complete_s
        or dark_age.feudal_click_s
        or 600.0
    )
    mil_duration_min = max(1.0, (game_duration_s - post_dark_start) / 60.0)
    production_rate = total_mil_units / mil_duration_min

    if production_rate >= 2.0 or total_mil_units >= 40:
        volume_comp = 100.0
    elif production_rate >= 1.2 or total_mil_units >= 20:
        volume_comp = 85.0
    elif production_rate >= 0.7 or total_mil_units >= 10:
        volume_comp = 70.0
    elif total_mil_units >= 4:
        volume_comp = 50.0
    elif total_mil_units >= 1:
        volume_comp = 35.0
    else:
        volume_comp = 15.0

    # Layer 4: Military Tech & Blacksmith Upgrade Alignment
    upgrades_count = 0
    if castle_age and castle_age.blacksmith_upgrades:
        upgrades_count += len(castle_age.blacksmith_upgrades)
    if imperial_age and imperial_age.key_upgrades:
        upgrades_count += len(imperial_age.key_upgrades)

    if upgrades_count >= 4:
        tech_comp = 100.0
    elif upgrades_count >= 2:
        tech_comp = 80.0
    elif upgrades_count >= 1:
        tech_comp = 60.0
    else:
        tech_comp = 25.0

    military_value = round(
        max(0.0, min(100.0, 0.40 * comp_comp + 0.35 * volume_comp + 0.25 * tech_comp)),
        1,
    )

    # -----------------------------------------------------------------------
    # 4. Overall Match Rating & Performance Grade (0 - 100%)
    # -----------------------------------------------------------------------
    m_score = micro_score if micro_score is not None else 70.0
    overall = round(
        0.25 * tc_uptime_pct + 0.30 * eco_efficiency + 0.25 * military_value + 0.20 * m_score,
        1,
    )

    if overall >= 90.0:
        grade = "S"
        rating = f"S ({overall}% - Top-Tier / 1600+ Elo Level)"
    elif overall >= 80.0:
        grade = "A"
        rating = f"A ({overall}% - Solid Competitive / 1200-1500 Elo)"
    elif overall >= 70.0:
        grade = "B"
        rating = f"B ({overall}% - Intermediate / 1000-1200 Elo)"
    elif overall >= 60.0:
        grade = "C"
        rating = f"C ({overall}% - Developing / 800-1000 Elo)"
    else:
        grade = "D"
        rating = f"D ({overall}% - Needs Fundamental Work / <800 Elo)"

    return PerformanceScores(
        tc_uptime_pct=tc_uptime_pct,
        tc_idle_pct=tc_idle_pct,
        eco_efficiency_score=eco_efficiency,
        military_value_score=military_value,
        total_military_units=total_mil_units,
        military_by_age=military_by_age,
        top_military_lines=top_military_lines,
        units_lost=units_lost,
        micro_score=micro_score,
        micro_apm=micro_apm,
        micro_style=micro_style,
        overall_score=overall,
        overall_grade=grade,
        overall_rating=rating,
    )
