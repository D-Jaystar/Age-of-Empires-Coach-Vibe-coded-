"""Strict Pydantic v2 BaseModel schemas for the AoE2 coaching pipeline."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 1. MatchMetadata
# ---------------------------------------------------------------------------
class MatchMetadata(BaseModel):
    """High-level information about the recorded match."""

    model_config = ConfigDict(frozen=False)

    map_name: str = Field(..., description="Name of the map played (e.g. 'Arabia', 'Arena').")
    map_size: str = Field(..., description="Map size descriptor (e.g. 'tiny', 'small', 'medium', 'large', 'giant').")
    game_duration_s: float = Field(..., description="Total game duration in seconds.")
    winner_name: str | None = Field(default=None, description="Name of the winning player, if determinable.")
    is_water_map: bool = Field(..., description="Whether the map is classified as a water map.")
    is_hybrid_map: bool = Field(..., description="Whether the map is classified as a hybrid (land + water) map.")
    game_version: str = Field(..., description="Game / patch version string.")
    save_version: float = Field(..., description="Replay save-file version number.")


# ---------------------------------------------------------------------------
# 2. PlayerInfo
# ---------------------------------------------------------------------------
class PlayerInfo(BaseModel):
    """Identity and basic positional data for a player."""

    model_config = ConfigDict(frozen=False)

    name: str = Field(..., description="In-game player name.")
    civilization: str = Field(..., description="Civilization chosen by the player.")
    color: str = Field(..., description="Player colour identifier.")
    number: int = Field(..., description="Player slot number (1-indexed).")
    tc_x: float | None = Field(default=None, description="X-coordinate of the starting Town Centre.")
    tc_y: float | None = Field(default=None, description="Y-coordinate of the starting Town Centre.")
    eapm: int | None = Field(default=None, description="Effective actions per minute.")
    winner: bool | None = Field(default=None, description="Whether this player won the game.")
    profile_id: int | None = Field(default=None, description="Online profile / account ID, if available.")
    civ_bonuses: list[str] = Field(default_factory=list, description="List of civilization bonuses.")
    civ_unique_units: list[str] = Field(default_factory=list, description="Civilization unique units.")
    civ_tech_restrictions: str | None = Field(default=None, description="Critical tech restrictions / missing technologies.")


# ---------------------------------------------------------------------------
# 3. BuildOrderEntry
# ---------------------------------------------------------------------------
class BuildOrderEntry(BaseModel):
    """A single timestamped action in a build order or upgrade timeline."""

    model_config = ConfigDict(frozen=False)

    timestamp_s: float = Field(..., description="Game-time timestamp in seconds when the action occurred.")
    action_type: str = Field(..., description="Category of the action (e.g. 'train', 'build', 'research').")
    param: str | None = Field(default=None, description="Parameter or target of the action (e.g. unit/building/tech name).")
    position_x: float | None = Field(default=None, description="X-coordinate where the action took place, if applicable.")
    position_y: float | None = Field(default=None, description="Y-coordinate where the action took place, if applicable.")


# ---------------------------------------------------------------------------
# 4. IdleTCGap
# ---------------------------------------------------------------------------
class IdleTCGap(BaseModel):
    """A period during which the Town Centre was idle (not producing)."""

    model_config = ConfigDict(frozen=False)

    start_s: float = Field(..., description="Start time of the idle gap in seconds.")
    end_s: float = Field(..., description="End time of the idle gap in seconds.")
    duration_s: float = Field(..., description="Duration of the idle gap in seconds.")
    context: str | None = Field(default=None, description="Situational context for the gap (e.g. 'near boar lure').")


# ---------------------------------------------------------------------------
# 5. DarkAgeMetrics
# ---------------------------------------------------------------------------
class DarkAgeMetrics(BaseModel):
    """Detailed metrics collected during the Dark Age."""

    model_config = ConfigDict(frozen=False)

    feudal_click_s: float | None = Field(default=None, description="Game-time in seconds when Feudal Age research was started.")
    feudal_complete_s: float | None = Field(default=None, description="Game-time in seconds when Feudal Age research completed.")
    estimated_vils_at_click: int | None = Field(default=None, description="Estimated villager count at the moment of Feudal click.")
    loom_time_s: float | None = Field(default=None, description="Game-time in seconds when Loom was researched.")
    loom_early: bool | None = Field(default=None, description="Whether Loom was researched earlier than the standard timing.")
    idle_tc_gaps: list[IdleTCGap] = Field(default_factory=list, description="List of periods where the TC was idle during Dark Age.")
    total_idle_tc_s: float = Field(..., description="Total accumulated TC idle time in seconds during Dark Age.")
    build_order: list[BuildOrderEntry] = Field(default_factory=list, description="Ordered list of build-order actions during Dark Age.")
    resource_gather_ratios: dict[str, float] = Field(
        default_factory=dict,
        description="Percentage breakdown of villager time on each resource (keys: 'wood', 'food', 'gold', 'stone').",
    )
    tc_distance_flags: list[str] = Field(
        default_factory=list,
        description="Flags highlighting inefficiencies relative to TC position (e.g. 'sheep gathered far from TC').",
    )


# ---------------------------------------------------------------------------
# 6. FeudalAgeMetrics
# ---------------------------------------------------------------------------
class FeudalAgeMetrics(BaseModel):
    """Detailed metrics collected during the Feudal Age."""

    model_config = ConfigDict(frozen=False)

    castle_click_s: float | None = Field(default=None, description="Game-time in seconds when Castle Age research was started.")
    castle_complete_s: float | None = Field(default=None, description="Game-time in seconds when Castle Age research completed.")
    opening_strategy: str = Field(
        ...,
        description="Detected opening strategy: 'scouts', 'archers', 'maa', 'fast_castle', 'boom', or 'unknown'.",
    )
    early_gold_flag: bool = Field(..., description="Whether gold was collected unusually early, hinting at a gold-unit opening.")
    first_farm_time_s: float | None = Field(default=None, description="Game-time in seconds when the first farm was seeded.")
    total_farms_built: int = Field(..., description="Total number of farms built during Feudal Age.")
    farm_build_rate: float | None = Field(default=None, description="Average rate of farm construction (farms per minute) during Feudal Age.")
    wheelbarrow_time_s: float | None = Field(default=None, description="Game-time in seconds when Wheelbarrow was researched.")
    wheelbarrow_vil_count: int | None = Field(default=None, description="Villager count at the time Wheelbarrow was researched.")
    tc_gather_point_description: str | None = Field(
        default=None,
        description="Textual description of where the TC gather point was set during Feudal Age.",
    )
    military_buildings: dict[str, int] = Field(
        default_factory=dict,
        description="Count of each military building type constructed during Feudal Age (e.g. {'Archery Range': 2}).",
    )


# ---------------------------------------------------------------------------
# 7. CastleAgeMetrics
# ---------------------------------------------------------------------------
class CastleAgeMetrics(BaseModel):
    """Detailed metrics collected during the Castle Age."""

    model_config = ConfigDict(frozen=False)

    imperial_click_s: float | None = Field(default=None, description="Game-time in seconds when Imperial Age research was started.")
    imperial_complete_s: float | None = Field(default=None, description="Game-time in seconds when Imperial Age research completed.")
    composition_focus_score: float | None = Field(
        default=None,
        description="Score (0-1) indicating how focused the army composition is; lower means more scattered.",
    )
    distinct_unit_lines: list[str] = Field(
        default_factory=list,
        description="List of distinct unit lines produced (e.g. ['knight', 'crossbowman']).",
    )
    unit_line_counts: dict[str, int] = Field(
        default_factory=dict,
        description="Number of units produced per unit line during Castle Age.",
    )
    production_buildings_added: dict[str, int] = Field(
        default_factory=dict,
        description="Count of each production building type added during Castle Age.",
    )
    blacksmith_upgrades: list[BuildOrderEntry] = Field(
        default_factory=list,
        description="Ordered list of Blacksmith upgrades researched during Castle Age.",
    )
    tc_count: int = Field(..., description="Total number of Town Centres the player has by the end of Castle Age.")
    scattered_composition_flag: bool = Field(
        ...,
        description="Flag indicating the army composition is too scattered across unit lines.",
    )


# ---------------------------------------------------------------------------
# 8. ImperialAgeMetrics
# ---------------------------------------------------------------------------
class ImperialAgeMetrics(BaseModel):
    """Metrics collected during the Imperial Age."""

    model_config = ConfigDict(frozen=False)

    key_upgrades: list[BuildOrderEntry] = Field(
        default_factory=list,
        description="Key upgrades researched during Imperial Age (e.g. Chemistry, unique techs).",
    )
    trebuchet_count: int | None = Field(default=None, description="Number of Trebuchets produced during Imperial Age.")


# ---------------------------------------------------------------------------
# 9. OpponentSummary
# ---------------------------------------------------------------------------
class OpponentSummary(BaseModel):
    """Condensed scouting-level overview of an opponent."""

    model_config = ConfigDict(frozen=False)

    name: str = Field(..., description="In-game name of the opponent.")
    civilization: str = Field(..., description="Civilization chosen by the opponent.")
    feudal_click_s: float | None = Field(default=None, description="Opponent's Feudal Age click time in seconds.")
    castle_click_s: float | None = Field(default=None, description="Opponent's Castle Age click time in seconds.")
    imperial_click_s: float | None = Field(default=None, description="Opponent's Imperial Age click time in seconds.")
    primary_unit_line: str | None = Field(default=None, description="Opponent's most-produced unit line, if detectable.")
    military_building_count: int | None = Field(default=None, description="Total number of military buildings the opponent constructed.")
    civ_focus: str | None = Field(default=None, description="Opponent civ focus/type (e.g. 'Cavalry', 'Archers').")
    civ_bonuses: list[str] = Field(default_factory=list, description="Opponent civ bonuses.")
    civ_unique_units: list[str] = Field(default_factory=list, description="Opponent unique units.")


# ---------------------------------------------------------------------------
# 9.5 PerformanceScores
# ---------------------------------------------------------------------------
class PerformanceScores(BaseModel):
    """Core benchmark percentages and efficiency metrics for executive summary."""

    model_config = ConfigDict(frozen=False)

    tc_uptime_pct: float = Field(..., description="Town Center active uptime percentage in Dark Age (100% - idle%).")
    tc_idle_pct: float = Field(..., description="Town Center idle time percentage in Dark Age.")
    eco_efficiency_score: float = Field(..., description="Overall economy management score (0-100%).")
    military_value_score: float = Field(..., description="Military focus and composition consistency score (0-100%).")
    total_military_units: int = Field(default=0, description="Total military units trained throughout the match.")


# ---------------------------------------------------------------------------
# 10. PlayerTelemetry
# ---------------------------------------------------------------------------
class PlayerTelemetry(BaseModel):
    """Full per-age telemetry bundle for the target player."""

    model_config = ConfigDict(frozen=False)

    player: PlayerInfo = Field(..., description="Identity and positional info for the player.")
    dark_age: DarkAgeMetrics = Field(..., description="Metrics collected during the Dark Age.")
    feudal_age: FeudalAgeMetrics | None = Field(default=None, description="Metrics collected during the Feudal Age, if reached.")
    castle_age: CastleAgeMetrics | None = Field(default=None, description="Metrics collected during the Castle Age, if reached.")
    imperial_age: ImperialAgeMetrics | None = Field(default=None, description="Metrics collected during the Imperial Age, if reached.")
    scores: PerformanceScores | None = Field(default=None, description="Key match performance scores and percentages.")


# ---------------------------------------------------------------------------
# 11. ParsedReplayReport
# ---------------------------------------------------------------------------
class ParsedReplayReport(BaseModel):
    """Complete structured output from the replay-parsing stage."""

    model_config = ConfigDict(frozen=False)

    metadata: MatchMetadata = Field(..., description="High-level match metadata.")
    target_player: PlayerTelemetry = Field(..., description="Full telemetry for the player being coached.")
    opponents: list[OpponentSummary] = Field(
        default_factory=list,
        description="Summary data for each opponent in the match.",
    )


# ---------------------------------------------------------------------------
# 12. CoachingReport
# ---------------------------------------------------------------------------
class CoachingReport(BaseModel):
    """Final human-readable coaching output produced by the LLM."""

    model_config = ConfigDict(frozen=False)

    replay_name: str = Field(..., description="File name (or identifier) of the analysed replay.")
    player_name: str = Field(..., description="Name of the player being coached.")
    language: str = Field(..., description="Language the report is written in (e.g. 'en', 'nl').")
    sections: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Coaching bullets grouped by section header (e.g. {'Dark Age': ['bullet1', 'bullet2']}).",
    )
    raw_response: str = Field(..., description="The unprocessed LLM response text.")
