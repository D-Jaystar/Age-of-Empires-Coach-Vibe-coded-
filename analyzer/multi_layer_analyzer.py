"""analyzer/multi_layer_analyzer.py
==================================

Assembles comprehensive, multi-layered diagnostic evaluation across:
1. Economy (Continuity, Resource Allocation, Spatial Micro, Eco Scaling)
2. Military (Volume/Pacing, Composition Synergy, Upgrade Alignment, Production Infrastructure)
3. Matchup & Strategy (Format & Role, Opening Execution, Tactical Adaptations)

Splits complex replay telemetry into clean, bite-sized analytical chunks
so the AI coach can evaluate game dynamics systematically without cognitive overload.
"""

from __future__ import annotations

from typing import Any, Optional

from data.models import (
    CastleAgeMetrics,
    DarkAgeMetrics,
    EconomyMultiLayer,
    FeudalAgeMetrics,
    ImperialAgeMetrics,
    MatchMetadata,
    MilitaryMultiLayer,
    MultiLayerAnalysis,
    OpponentSummary,
    PerformanceScores,
    PlayerInfo,
    StrategyMultiLayer,
)


def build_multi_layer_analysis(
    metadata: MatchMetadata,
    player_info: PlayerInfo,
    dark_age: DarkAgeMetrics,
    feudal_age: Optional[FeudalAgeMetrics] = None,
    castle_age: Optional[CastleAgeMetrics] = None,
    imperial_age: Optional[ImperialAgeMetrics] = None,
    scores: Optional[PerformanceScores] = None,
    opponents: Optional[list[OpponentSummary]] = None,
) -> MultiLayerAnalysis:
    """Build a comprehensive, chunked MultiLayerAnalysis for the coached match."""

    # =======================================================================
    # 1. ECONOMY MULTI-LAYER
    # =======================================================================
    # Layer 1A: Continuity & Uptime
    idle_tc_s = dark_age.total_idle_tc_s
    uptime_pct = scores.tc_uptime_pct if scores else 0.0
    idle_pct = scores.tc_idle_pct if scores else 0.0

    continuity_data: dict[str, Any] = {
        "tc_uptime_pct": uptime_pct,
        "tc_idle_pct": idle_pct,
        "total_idle_tc_seconds": idle_tc_s,
        "idle_gaps_count": len(dark_age.idle_tc_gaps),
        "notable_gaps": [
            f"{g.start_s:.0f}s - {g.end_s:.0f}s ({g.duration_s:.0f}s)" + (f" [{g.context}]" if g.context else "")
            for g in dark_age.idle_tc_gaps[:3]
        ],
        "vils_at_feudal_click": dark_age.estimated_vils_at_click,
        "loom_time_s": dark_age.loom_time_s,
        "loom_assessment": "Early Loom" if dark_age.loom_early else ("Standard / Delayed" if dark_age.loom_time_s else "Unrecorded"),
    }

    # Layer 1B: Resource Allocation & Food Engine
    first_farm = feudal_age.first_farm_time_s if feudal_age else None
    tot_farms = feudal_age.total_farms_built if feudal_age else 0
    farm_rate = feudal_age.farm_build_rate if feudal_age else 0.0
    early_gold = feudal_age.early_gold_flag if feudal_age else False

    allocation_data: dict[str, Any] = {
        "dark_age_gather_ratios": dark_age.resource_gather_ratios,
        "early_gold_mined_flag": early_gold,
        "first_farm_time_s": first_farm,
        "total_farms_built": tot_farms,
        "farm_build_rate_per_min": farm_rate,
        "food_engine_type": "Water Fish Macro" if (metadata.is_water_map or metadata.is_hybrid_map) and tot_farms <= 2 else "Land Farming",
    }

    # Layer 1C: Spatial Micro & Walking Penalties
    spatial_data: dict[str, Any] = {
        "distance_flags": dark_age.tc_distance_flags,
        "tc_gather_point": feudal_age.tc_gather_point_description if feudal_age else None,
        "walking_efficiency": "High (clean lures)" if not dark_age.tc_distance_flags else f"Walking penalty ({len(dark_age.tc_distance_flags)} distant harvest events)",
    }

    # Layer 1D: Technology & Eco Scaling
    scaling_data: dict[str, Any] = {
        "wheelbarrow_time_s": feudal_age.wheelbarrow_time_s if feudal_age else None,
        "wheelbarrow_vil_count": feudal_age.wheelbarrow_vil_count if feudal_age else None,
        "tc_count_castle_age": castle_age.tc_count if castle_age else 1,
        "eco_boom_style": (
            "3+ TC Macro Boom" if (castle_age and castle_age.tc_count >= 3)
            else "2 TC Balanced Play" if (castle_age and castle_age.tc_count == 2)
            else "1 TC Aggressive / Fast Castle"
        ),
    }

    economy_layer = EconomyMultiLayer(
        continuity=continuity_data,
        resource_allocation=allocation_data,
        spatial_efficiency=spatial_data,
        eco_scaling=scaling_data,
    )

    # =======================================================================
    # 2. MILITARY MULTI-LAYER
    # =======================================================================
    total_units = scores.total_military_units if scores else 0
    by_age = scores.military_by_age if scores else {}
    top_lines = scores.top_military_lines if scores else {}

    mil_duration_min = max(1.0, (metadata.game_duration_s - (dark_age.feudal_complete_s or dark_age.feudal_click_s or 600.0)) / 60.0)
    units_per_min = round(total_units / mil_duration_min, 1)

    volume_pacing_data: dict[str, Any] = {
        "total_military_units": total_units,
        "units_by_age": by_age,
        "units_per_minute_active": units_per_min,
        "volume_rating": "Mass Army (>1.5/min)" if units_per_min >= 1.5 else "Moderate Army" if units_per_min >= 0.8 else "Low Army Output",
    }

    primary_line = list(top_lines.keys())[0] if top_lines else "None"
    primary_count = list(top_lines.values())[0] if top_lines else 0
    secondary_line = list(top_lines.keys())[1] if len(top_lines) > 1 else None
    secondary_count = list(top_lines.values())[1] if len(top_lines) > 1 else 0

    comp_focus = castle_age.composition_focus_score if castle_age else 0.85
    is_scattered = castle_age.scattered_composition_flag if castle_age else False

    composition_data: dict[str, Any] = {
        "primary_unit_line": f"{primary_line} ({primary_count} units)",
        "secondary_unit_line": f"{secondary_line} ({secondary_count} units)" if secondary_line else "None",
        "distinct_lines_count": len(top_lines),
        "all_lines_breakdown": top_lines,
        "composition_focus_score": comp_focus,
        "scattered_composition_flag": is_scattered,
        "army_archetype": (
            f"Focused {primary_line} Core" if comp_focus >= 0.85
            else f"Hybrid ({primary_line} + {secondary_line or 'Trash'})" if comp_focus >= 0.70
            else "Scattered multi-line army"
        ),
    }

    # Upgrades & Tech Alignment
    ca_upgrades = [str(u.param) for u in (castle_age.blacksmith_upgrades if castle_age else []) if u.param]
    imp_upgrades = [str(u.param) for u in (imperial_age.key_upgrades if imperial_age else []) if u.param]
    all_mil_upgrades = ca_upgrades + imp_upgrades

    upgrade_data: dict[str, Any] = {
        "blacksmith_upgrades": ca_upgrades,
        "imperial_key_upgrades": imp_upgrades,
        "total_military_upgrades_count": len(all_mil_upgrades),
        "upgrade_alignment_evaluation": (
            "Fully Upgraded" if len(all_mil_upgrades) >= 4
            else "Moderately Upgraded" if len(all_mil_upgrades) >= 2
            else "Under-Upgraded / Missing Armor or Attack"
        ),
    }

    prod_feudal = feudal_age.military_buildings if feudal_age else {}
    prod_castle = castle_age.production_buildings_added if castle_age else {}
    infrastructure_data: dict[str, Any] = {
        "feudal_military_buildings": prod_feudal,
        "castle_age_production_added": prod_castle,
        "trebuchet_count": imperial_age.trebuchet_count if imperial_age else 0,
    }

    military_layer = MilitaryMultiLayer(
        volume_pacing=volume_pacing_data,
        composition_synergy=composition_data,
        upgrade_alignment=upgrade_data,
        production_infrastructure=infrastructure_data,
    )

    # =======================================================================
    # 3. STRATEGY & MATCHUP MULTI-LAYER
    # =======================================================================
    gmode = metadata.gamemode or "Random Map"
    mpos = metadata.map_position or ("Solo (1v1)" if len(opponents or []) <= 1 else "Flank")

    role_data: dict[str, Any] = {
        "gamemode": gmode,
        "map_position": mpos,
        "map_environment": "Water Map" if metadata.is_water_map else "Hybrid Map" if metadata.is_hybrid_map else "Land Map",
        "expected_role_responsibility": (
            "Pocket: Fast Castle, Knights/Cavalry mobility, economic boom, assist flanks" if "pocket" in mpos.lower()
            else "Flank: Early Feudal aggression, archery/scouts, forward walling, survive early enemy pressure" if "flank" in mpos.lower()
            else "1v1: Dictate match tempo, counter enemy civ power units, control neutral resources"
        ),
    }

    opening_strat = feudal_age.opening_strategy if feudal_age else "none"
    opening_data: dict[str, Any] = {
        "detected_opening": opening_strat,
        "player_civ": player_info.civilization,
        "civ_bonuses_leveraged": player_info.civ_bonuses[:2] if player_info.civ_bonuses else [],
        "opening_synergy": f"{opening_strat.title()} with {player_info.civilization}",
    }

    # Tactical Adaptations
    opp_names = [f"{o.name} ({o.civilization})" for o in (opponents or [])]
    adaptation_data: dict[str, Any] = {
        "opponents_roster": opp_names,
        "notable_tactical_counters": (
            f"Infantry adaptation ({top_lines.get('Militia line', 0)} Militia line) deployed against spearman/halb threats"
            if top_lines.get("Militia line", 0) >= 15
            else "Heavy cavalry focus Dictating tempo"
            if top_lines.get("Knight line", 0) >= 20
            else "Standard unit line execution"
        ),
    }

    strategy_layer = StrategyMultiLayer(
        format_and_role=role_data,
        opening_execution=opening_data,
        tactical_adaptations=adaptation_data,
    )

    return MultiLayerAnalysis(
        economy=economy_layer,
        military=military_layer,
        strategy=strategy_layer,
    )
