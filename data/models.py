"""data/models.py - Strict Pydantic v2 schemas for AoE2 match telemetry and coaching."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class MatchMetadata(BaseModel):
    """High-level information about the recorded match."""
    map_name: str
    map_size: str
    game_duration_s: float
    winner_name: str | None = None
    is_water_map: bool
    is_hybrid_map: bool
    game_version: str
    save_version: float
    gamemode: str = "Random Map"
    diplomacy: str | None = None
    map_position: str | None = None


class PlayerInfo(BaseModel):
    """Identity, position, and civ traits for a player."""
    name: str
    civilization: str
    color: str
    number: int
    tc_x: float | None = None
    tc_y: float | None = None
    eapm: int | None = None
    winner: bool | None = None
    profile_id: int | None = None
    civ_bonuses: list[str] = Field(default_factory=list)
    civ_unique_units: list[str] = Field(default_factory=list)
    civ_tech_restrictions: str | None = None


class BuildOrderEntry(BaseModel):
    """A single timestamped action in a build order or upgrade timeline."""
    timestamp_s: float
    action_type: str
    param: str | None = None
    position_x: float | None = None
    position_y: float | None = None


class IdleTCGap(BaseModel):
    """A period during which the Town Center was idle."""
    start_s: float
    end_s: float
    duration_s: float
    context: str | None = None


class DarkAgeMetrics(BaseModel):
    """Detailed metrics collected during the Dark Age."""
    feudal_click_s: float | None = None
    feudal_complete_s: float | None = None
    estimated_vils_at_click: int | None = None
    loom_time_s: float | None = None
    loom_early: bool | None = None
    idle_tc_gaps: list[IdleTCGap] = Field(default_factory=list)
    total_idle_tc_s: float
    build_order: list[BuildOrderEntry] = Field(default_factory=list)
    resource_gather_ratios: dict[str, float] = Field(default_factory=dict)
    tc_distance_flags: list[str] = Field(default_factory=list)
    farms_built: int = 0
    first_farm_time_s: float | None = None


class FeudalAgeMetrics(BaseModel):
    """Metrics collected during the Feudal Age."""
    castle_click_s: float | None = None
    castle_complete_s: float | None = None
    opening_strategy: str
    early_gold_flag: bool
    first_farm_time_s: float | None = None
    total_farms_built: int
    farm_build_rate: float
    wheelbarrow_time_s: float | None = None
    wheelbarrow_vil_count: int | None = None
    tc_gather_point_description: str | None = None
    military_buildings: dict[str, int] = Field(default_factory=dict)
    military_units_trained: int = 0
    unit_line_counts: dict[str, int] = Field(default_factory=dict)
    resource_gather_ratios: dict[str, float] = Field(default_factory=dict)


class CastleAgeMetrics(BaseModel):
    """Metrics collected during the Castle Age."""
    imperial_click_s: float | None = None
    imperial_complete_s: float | None = None
    composition_focus_score: float
    distinct_unit_lines: list[str] = Field(default_factory=list)
    unit_line_counts: dict[str, int] = Field(default_factory=dict)
    military_units_trained: int = 0
    production_buildings_added: dict[str, int] = Field(default_factory=dict)
    blacksmith_upgrades: list[BuildOrderEntry] = Field(default_factory=list)
    tc_count: int
    scattered_composition_flag: bool


class ImperialAgeMetrics(BaseModel):
    """Metrics collected during the Imperial Age."""
    military_units_trained: int = 0
    unit_line_counts: dict[str, int] = Field(default_factory=dict)
    key_upgrades: list[BuildOrderEntry] = Field(default_factory=list)
    trebuchet_count: int | None = None


class OpponentSummary(BaseModel):
    """Condensed scouting-level overview of an opponent."""
    name: str
    civilization: str
    feudal_click_s: float | None = None
    castle_click_s: float | None = None
    imperial_click_s: float | None = None
    primary_unit_line: str | None = None
    military_building_count: int | None = None
    civ_focus: str | None = None
    civ_bonuses: list[str] = Field(default_factory=list)
    civ_unique_units: list[str] = Field(default_factory=list)


class PerformanceScores(BaseModel):
    """Core benchmark percentages and efficiency metrics for executive summary."""
    tc_uptime_pct: float
    tc_idle_pct: float
    eco_efficiency_score: float
    military_value_score: float
    total_military_units: int = 0
    military_by_age: dict[str, int] = Field(default_factory=dict)
    top_military_lines: dict[str, int] = Field(default_factory=dict)
    units_lost: int | None = None
    micro_score: float | None = None
    micro_apm: float | None = None
    micro_style: str | None = None
    overall_score: float = 0.0
    overall_grade: str = "B"
    overall_rating: str = "B (75.0%)"


class EconomyMultiLayer(BaseModel):
    """Chunked analytical layer for economy continuity, allocation, and scaling."""
    continuity: dict[str, Any] = Field(default_factory=dict)
    resource_allocation: dict[str, Any] = Field(default_factory=dict)
    spatial_efficiency: dict[str, Any] = Field(default_factory=dict)
    eco_scaling: dict[str, Any] = Field(default_factory=dict)


class MilitaryMultiLayer(BaseModel):
    """Chunked analytical layer for military volume, composition, and upgrades."""
    volume_pacing: dict[str, Any] = Field(default_factory=dict)
    composition_synergy: dict[str, Any] = Field(default_factory=dict)
    upgrade_alignment: dict[str, Any] = Field(default_factory=dict)
    production_infrastructure: dict[str, Any] = Field(default_factory=dict)
    combat_and_micro: dict[str, Any] = Field(default_factory=dict)


class StrategyMultiLayer(BaseModel):
    """Chunked analytical layer for format, role, opening, and tactical counters."""
    format_and_role: dict[str, Any] = Field(default_factory=dict)
    opening_execution: dict[str, Any] = Field(default_factory=dict)
    tactical_adaptations: dict[str, Any] = Field(default_factory=dict)


class MultiLayerAnalysis(BaseModel):
    """Holistic multi-layer breakdown dividing complex match data into focused chunks."""
    economy: EconomyMultiLayer = Field(default_factory=EconomyMultiLayer)
    military: MilitaryMultiLayer = Field(default_factory=MilitaryMultiLayer)
    strategy: StrategyMultiLayer = Field(default_factory=StrategyMultiLayer)


class PlayerTelemetry(BaseModel):
    """Full per-age telemetry bundle for the target player."""
    player: PlayerInfo
    dark_age: DarkAgeMetrics
    feudal_age: FeudalAgeMetrics | None = None
    castle_age: CastleAgeMetrics | None = None
    imperial_age: ImperialAgeMetrics | None = None
    scores: PerformanceScores | None = None
    multi_layer: MultiLayerAnalysis | None = None


class ParsedReplayReport(BaseModel):
    """Complete structured output from the replay-parsing stage."""
    metadata: MatchMetadata
    target_player: PlayerTelemetry
    opponents: list[OpponentSummary] = Field(default_factory=list)


class CoachingReport(BaseModel):
    """Final human-readable coaching output produced by the LLM."""
    replay_name: str
    player_name: str
    language: str
    sections: dict[str, list[str]] = Field(default_factory=dict)
    raw_response: str
