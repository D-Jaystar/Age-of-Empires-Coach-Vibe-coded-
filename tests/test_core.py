"""tests/test_core.py
===================

Comprehensive test suite verifying:
- Input validation & Guard Clauses
- Age segmentation
- Town Center idle gap calculation & boar lure context cross-referencing
- Economic & military heuristics
- Spatial micro checks
- JSON and Markdown export functionality
- Pydantic models serialization
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ai.coach_client import validate_api_key
from analyzer.age_segmenter import (
    AgeSegment,
    filter_events_by_age,
    get_age_at_timestamp,
    segment_by_age,
)
from analyzer.economy_heuristics import (
    calculate_idle_tc_gaps,
    calculate_resource_gather_ratios,
    detect_farm_timing,
    detect_loom_timing,
    detect_wheelbarrow_timing,
    estimate_vils_at_feudal_click,
    extract_build_order,
)
from analyzer.military_heuristics import (
    calculate_composition_focus,
    count_military_buildings,
    count_production_scaling,
    detect_early_gold,
    detect_opening_strategy,
    extract_blacksmith_upgrades,
)
from analyzer.performance_scorer import calculate_performance_scores
from analyzer.spatial_heuristics import (
    check_gather_distances,
    check_tc_gather_point,
    detect_water_map_objects,
    euclidean_distance,
    format_timestamp,
)
from data.exceptions import (
    AIAnalysisError,
    PlayerNotFoundError,
    ReplayLoadError,
)
from data.models import (
    CoachingReport,
    DarkAgeMetrics,
    IdleTCGap,
    MatchMetadata,
    OpponentSummary,
    ParsedReplayReport,
    PlayerInfo,
    PlayerTelemetry,
)
from exporter.readable_exporter import (
    export_coaching,
    export_json,
    export_markdown,
    format_duration,
    truncate_payload_for_llm,
)
from parser.replay_loader import validate_replay_path


# ===========================================================================
# 1. Guard Clause Tests
# ===========================================================================

def test_validate_replay_path_none() -> None:
    with pytest.raises(ReplayLoadError, match="cannot be None"):
        validate_replay_path(None)


def test_validate_replay_path_empty_string() -> None:
    with pytest.raises(ReplayLoadError, match="empty string"):
        validate_replay_path("   ")


def test_validate_replay_path_not_exists() -> None:
    with pytest.raises(ReplayLoadError, match="File does not exist"):
        validate_replay_path("non_existent_file.aoe2record")


def test_validate_replay_path_directory(tmp_path: Path) -> None:
    dir_path = tmp_path / "somedir"
    dir_path.mkdir()
    with pytest.raises(ReplayLoadError, match="Expected a file, but found a directory"):
        validate_replay_path(dir_path)


def test_validate_replay_path_wrong_extension(tmp_path: Path) -> None:
    txt_file = tmp_path / "match.txt"
    txt_file.write_text("dummy")
    with pytest.raises(ReplayLoadError, match="Invalid file extension"):
        validate_replay_path(txt_file)


def test_validate_replay_path_empty_file(tmp_path: Path) -> None:
    empty_replay = tmp_path / "match.aoe2record"
    empty_replay.touch()
    with pytest.raises(ReplayLoadError, match="empty \\(0 bytes\\)"):
        validate_replay_path(empty_replay)


def test_player_not_found_error_lists_available() -> None:
    err = PlayerNotFoundError("TheViper", ["Hera", "Daut", "Liereyy"])
    err_str = str(err)
    assert "TheViper" in err_str
    assert "Hera" in err_str
    assert "Daut" in err_str
    assert "Liereyy" in err_str


def test_missing_api_key_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(AIAnalysisError, match="GEMINI_API_KEY is not set"):
        validate_api_key()


# ===========================================================================
# 2. Age Segmentation Tests
# ===========================================================================

def test_full_game_segmentation() -> None:
    uptimes = {"feudal": 600.0, "castle": 1200.0, "imperial": 1800.0}
    segments = segment_by_age(uptimes, game_duration_s=2400.0)

    assert len(segments) == 4
    assert segments[0].age_name == "Dark Age"
    assert segments[0].start_s == 0.0
    assert segments[0].end_s == 600.0

    assert segments[1].age_name == "Feudal Age"
    assert segments[1].start_s == 600.0
    assert segments[1].end_s == 1200.0

    assert segments[2].age_name == "Castle Age"
    assert segments[2].start_s == 1200.0
    assert segments[2].end_s == 1800.0

    assert segments[3].age_name == "Imperial Age"
    assert segments[3].start_s == 1800.0
    assert segments[3].end_s == 2400.0


def test_dark_age_only() -> None:
    segments = segment_by_age({}, game_duration_s=900.0)
    assert len(segments) == 1
    assert segments[0].age_name == "Dark Age"
    assert segments[0].end_s == 900.0


def test_filter_events_by_age() -> None:
    segments = [
        AgeSegment("Dark Age", 0.0, 500.0),
        AgeSegment("Feudal Age", 500.0, 1000.0),
    ]
    events = [
        {"timestamp_s": 50.0, "param": "House"},
        {"timestamp_s": 499.0, "param": "Villager"},
        {"timestamp_s": 500.0, "param": "Stable"},
        {"timestamp_s": 750.0, "param": "Archery Range"},
    ]
    buckets = filter_events_by_age(events, segments)
    assert len(buckets["Dark Age"]) == 2
    assert len(buckets["Feudal Age"]) == 2


def test_get_age_at_timestamp() -> None:
    segments = [
        AgeSegment("Dark Age", 0.0, 500.0),
        AgeSegment("Feudal Age", 500.0, 1000.0),
    ]
    assert get_age_at_timestamp(250.0, segments) == "Dark Age"
    assert get_age_at_timestamp(500.0, segments) == "Feudal Age"
    assert get_age_at_timestamp(800.0, segments) == "Feudal Age"


# ===========================================================================
# 3. Idle TC Gap Tests
# ===========================================================================

def test_no_gaps_continuous_production() -> None:
    # 5 villagers queued back to back: 0, 25, 50, 75, 100 -> busy up to 125
    events = [
        {"timestamp_s": float(i * 25), "type": "Queue", "param": "Villager"}
        for i in range(5)
    ]
    gaps, total_idle = calculate_idle_tc_gaps(events, feudal_click_s=125.0, game_duration_s=500.0)
    assert len(gaps) == 0
    assert total_idle == 0.0


def test_single_idle_tc_gap() -> None:
    # Vil 1 queued at 0 (finishes 25).
    # Then gap until 70 (gap of 45s). Vil 2 queued at 70 (finishes 95).
    events = [
        {"timestamp_s": 0.0, "type": "Queue", "param": "Villager"},
        {"timestamp_s": 70.0, "type": "Queue", "param": "Villager"},
    ]
    gaps, total_idle = calculate_idle_tc_gaps(events, feudal_click_s=95.0, game_duration_s=500.0)
    assert len(gaps) == 1
    assert gaps[0].start_s == 25.0
    assert gaps[0].end_s == 70.0
    assert gaps[0].duration_s == 45.0


def test_idle_tc_gap_near_boar() -> None:
    # Vil 1 queued at 0 (finishes 25).
    # Gap until 80s (duration 55s). Boar gather command at 35s.
    events = [
        {"timestamp_s": 0.0, "type": "Queue", "param": "Villager"},
        {"timestamp_s": 35.0, "type": "Gather", "param": "Wild Boar"},
        {"timestamp_s": 80.0, "type": "Queue", "param": "Villager"},
    ]
    gaps, _ = calculate_idle_tc_gaps(events, feudal_click_s=105.0, game_duration_s=500.0)
    assert len(gaps) == 1
    assert gaps[0].context == "near boar lure"


# ===========================================================================
# 4. Economy Heuristics Tests
# ===========================================================================

def test_estimate_vils_at_feudal_click() -> None:
    events = [
        {"timestamp_s": 10.0, "param": "Villager"},
        {"timestamp_s": 35.0, "param": "Villager"},
        {"timestamp_s": 60.0, "param": "Villager"},
        {"timestamp_s": 600.0, "param": "Villager"},  # After feudal click
    ]
    vils = estimate_vils_at_feudal_click(events, feudal_click_s=500.0)
    # 3 base + 3 before feudal = 6
    assert vils == 6


def test_detect_loom_timing_early() -> None:
    events = [
        {"timestamp_s": 50.0, "type": "Research", "param": "Loom"},
    ]
    loom_time, is_early = detect_loom_timing(events, feudal_click_s=500.0)
    assert loom_time == 50.0
    assert is_early is True


def test_detect_loom_timing_late() -> None:
    events = [
        {"timestamp_s": float(i * 25), "param": "Villager"} for i in range(16)
    ]
    events.append({"timestamp_s": 450.0, "type": "Research", "param": "Loom"})
    loom_time, is_early = detect_loom_timing(events, feudal_click_s=480.0)
    assert loom_time == 450.0
    assert is_early is False


def test_resource_gather_ratios() -> None:
    events = [
        {"timestamp_s": 10.0, "param": "Sheep", "type": "Gather"},
        {"timestamp_s": 20.0, "param": "Boar", "type": "Gather"},
        {"timestamp_s": 30.0, "param": "Lumber Camp", "type": "Build"},
        {"timestamp_s": 40.0, "param": "Mining Camp", "type": "Build"},
    ]
    ratios = calculate_resource_gather_ratios(events, 0.0, 100.0)
    assert ratios["food"] == 0.50
    assert ratios["wood"] == 0.25
    assert ratios["gold"] == 0.25


def test_farm_timing() -> None:
    events = [
        {"timestamp_s": 600.0, "type": "Build", "param": "Farm"},
        {"timestamp_s": 660.0, "type": "Build", "param": "Farm"},
        {"timestamp_s": 720.0, "type": "Build", "param": "Farm"},
    ]
    first_farm, count, rate = detect_farm_timing(events, start_s=500.0, end_s=800.0)
    assert first_farm == 600.0
    assert count == 3
    # 3 farms over 300s (5 minutes) = 0.6 farms/min
    assert rate == 0.6


def test_detect_wheelbarrow_timing() -> None:
    events = [
        {"timestamp_s": float(i * 25), "param": "Villager"} for i in range(15)
    ]
    events.append({"timestamp_s": 700.0, "type": "Research", "param": "Wheelbarrow"})
    wb_time, vil_count = detect_wheelbarrow_timing(events)
    assert wb_time == 700.0
    assert vil_count == 18  # 3 start + 15 trained


# ===========================================================================
# 5. Military Heuristics Tests
# ===========================================================================

def test_detect_scouts_opening() -> None:
    feudal_events = [
        {"timestamp_s": 650.0, "type": "Build", "param": "Stable"},
        {"timestamp_s": 700.0, "type": "Queue", "param": "Scout Cavalry"},
    ]
    opening = detect_opening_strategy(feudal_events, dark_events=[])
    assert opening == "scouts"


def test_detect_archers_opening() -> None:
    feudal_events = [
        {"timestamp_s": 650.0, "type": "Build", "param": "Archery Range"},
        {"timestamp_s": 700.0, "type": "Queue", "param": "Archer"},
    ]
    opening = detect_opening_strategy(feudal_events, dark_events=[])
    assert opening == "archers"


def test_detect_maa_opening() -> None:
    dark_events = [
        {"timestamp_s": 400.0, "type": "Build", "param": "Barracks"},
        {"timestamp_s": 450.0, "type": "Queue", "param": "Militia"},
        {"timestamp_s": 475.0, "type": "Queue", "param": "Militia"},
    ]
    feudal_events = [
        {"timestamp_s": 620.0, "type": "Build", "param": "Archery Range"},
    ]
    opening = detect_opening_strategy(feudal_events, dark_events)
    assert opening == "maa"


def test_composition_focus_focused() -> None:
    events = [
        {"timestamp_s": 1300.0, "type": "Queue", "param": "Knight"},
        {"timestamp_s": 1330.0, "type": "Queue", "param": "Knight"},
    ]
    score, lines, counts, is_scattered = calculate_composition_focus(events, 1200.0, 1800.0)
    assert score == 1.0
    assert "Knight line" in lines
    assert is_scattered is False


def test_composition_focus_scattered() -> None:
    events = [
        {"timestamp_s": 1300.0, "type": "Queue", "param": "Knight"},
        {"timestamp_s": 1310.0, "type": "Queue", "param": "Archer"},
        {"timestamp_s": 1320.0, "type": "Queue", "param": "Pikeman"},
        {"timestamp_s": 1330.0, "type": "Queue", "param": "Mangonel"},
    ]
    score, lines, counts, is_scattered = calculate_composition_focus(events, 1200.0, 1800.0)
    assert score == 0.25
    assert len(lines) == 4
    assert is_scattered is True


# ===========================================================================
# 6. Spatial Heuristics Tests
# ===========================================================================

def test_euclidean_distance() -> None:
    assert euclidean_distance(0.0, 0.0, 3.0, 4.0) == 5.0
    assert euclidean_distance(None, 0.0, 3.0, 4.0) == 0.0


def test_check_gather_distances_flags_distant_animals() -> None:
    # TC at (50, 50). Sheep at (50, 58) -> dist 8 > 5 threshold
    events = [
        {"timestamp_s": 120.0, "param": "Sheep", "position_x": 50.0, "position_y": 58.0},
    ]
    flags = check_gather_distances(events, tc_x=50.0, tc_y=50.0)
    assert len(flags) == 1
    assert "Herdable animal harvested" in flags[0]
    assert "8.0 tiles" in flags[0]


def test_check_gather_distances_valid_boar_lure_not_flagged() -> None:
    # TC at (50, 50). 1 vil lures boar at dist 18 (50, 68) at t=100.
    # At t=135 (within 75s), villagers gather boar at (50, 52) dist 2.
    events = [
        {
            "timestamp_s": 100.0,
            "param": "Wild Boar",
            "position_x": 50.0,
            "position_y": 68.0,
            "payload": {"target_id": 999, "object_ids": [101]},
        },
        {
            "timestamp_s": 135.0,
            "param": "Wild Boar",
            "position_x": 50.0,
            "position_y": 52.0,
            "payload": {"target_id": 999, "object_ids": [101, 102, 103, 104]},
        },
    ]
    flags = check_gather_distances(events, tc_x=50.0, tc_y=50.0)
    assert len(flags) == 0


def test_check_gather_distances_wild_boar_harvest_flagged() -> None:
    # TC at (50, 50). 4 vils harvesting boar far away at (50, 70) dist 20.
    events = [
        {
            "timestamp_s": 100.0,
            "param": "Wild Boar",
            "position_x": 50.0,
            "position_y": 70.0,
            "payload": {"target_id": 999, "object_ids": [101, 102, 103, 104]},
        },
    ]
    flags = check_gather_distances(events, tc_x=50.0, tc_y=50.0)
    assert len(flags) == 1
    assert "Boar harvested 20.0 tiles away" in flags[0]


def test_check_gather_distances_deer_flagged() -> None:
    # TC at (50, 50). Deer gathered at (50, 65) dist 15.
    events = [
        {
            "timestamp_s": 150.0,
            "param": "Deer",
            "position_x": 50.0,
            "position_y": 65.0,
            "payload": {"object_ids": [101]},
        },
    ]
    flags = check_gather_distances(events, tc_x=50.0, tc_y=50.0)
    assert len(flags) == 1
    assert "Deer/huntable animal harvested" in flags[0]


def test_check_gather_distances_opening_sheep_shift_click_not_flagged() -> None:
    # Opening 30s: villagers shift-clicked onto sheep at 8 tiles while building houses
    events = [
        {
            "timestamp_s": 5.0,
            "param": "Sheep",
            "position_x": 50.0,
            "position_y": 58.0,
            "payload": {"object_ids": [1, 2]},
        },
        {
            "timestamp_s": 8.0,
            "param": "Sheep",
            "position_x": 50.0,
            "position_y": 56.0,
            "payload": {"object_ids": [3]},
        },
    ]
    flags = check_gather_distances(events, tc_x=50.0, tc_y=50.0)
    # Must NOT be flagged as remote harvest!
    assert len(flags) == 0


def test_check_gather_distances_boar_and_deer_lure() -> None:
    events = [
        # Boar clicked with 3 villagers 18 tiles away, brought under TC (2 tiles away) within 90s
        {
            "timestamp_s": 260.0,
            "param": "Wild Boar",
            "position_x": 68.0,
            "position_y": 50.0,
            "payload": {"object_ids": [1, 2, 3], "target_id": 5001},
        },
        {
            "timestamp_s": 320.0,
            "param": "Wild Boar",
            "position_x": 51.5,
            "position_y": 50.5,
            "payload": {"object_ids": [1, 2, 3], "target_id": 5001},
        },
        # Deer clicked 14 tiles away, pushed and slaughtered under TC (1.5 tiles away)
        {
            "timestamp_s": 400.0,
            "param": "Deer",
            "position_x": 64.0,
            "position_y": 50.0,
            "payload": {"object_ids": [4], "target_id": 4001},
        },
        {
            "timestamp_s": 500.0,
            "param": "Deer",
            "position_x": 50.5,
            "position_y": 51.0,
            "payload": {"object_ids": [4, 5], "target_id": 4001},
        },
    ]
    flags = check_gather_distances(events, tc_x=50.0, tc_y=50.0)
    assert len(flags) == 0


def test_bulgarian_civ_tech_restrictions_in_prompt() -> None:
    from ai.prompt_builder import build_system_prompt

    prompt = build_system_prompt(language="en", target_civ="Bulgarians")
    assert "NO PALADIN" in prompt
    assert "Bagains" in prompt


def test_format_timestamp() -> None:
    assert format_timestamp(45.0) == "00:45"
    assert format_timestamp(615.0) == "10:15"
    assert format_timestamp(3665.0) == "01:01:05"
    assert format_timestamp(None) == "00:00"


# ===========================================================================
# 7. Exporter & Serialization Tests
# ===========================================================================

def _create_sample_report() -> ParsedReplayReport:
    return ParsedReplayReport(
        metadata=MatchMetadata(
            map_name="Arabia",
            map_size="tiny",
            game_duration_s=1800.0,
            winner_name="Hera",
            is_water_map=False,
            is_hybrid_map=False,
            game_version="101.102.30000",
            save_version=12.5,
        ),
        target_player=PlayerTelemetry(
            player=PlayerInfo(
                name="Hera",
                civilization="Franks",
                color="Blue",
                number=1,
                tc_x=50.0,
                tc_y=50.0,
                eapm=85,
                winner=True,
            ),
            dark_age=DarkAgeMetrics(
                feudal_click_s=480.0,
                feudal_complete_s=610.0,
                estimated_vils_at_click=20,
                loom_time_s=455.0,
                loom_early=False,
                idle_tc_gaps=[],
                total_idle_tc_s=12.5,
                build_order=[],
                resource_gather_ratios={"food": 0.6, "wood": 0.35, "gold": 0.05, "stone": 0.0},
                tc_distance_flags=[],
            ),
        ),
        opponents=[
            OpponentSummary(
                name="TheViper",
                civilization="Britons",
                feudal_click_s=500.0,
            )
        ],
    )


def test_json_and_markdown_export(tmp_path: Path) -> None:
    report = _create_sample_report()
    json_path = export_json(report, output_dir=tmp_path, replay_name="sample")
    md_path = export_markdown(report, output_dir=tmp_path, replay_name="sample")

    assert json_path.exists()
    assert md_path.exists()

    # Verify JSON content
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["metadata"]["map_name"] == "Arabia"
    assert data["target_player"]["player"]["name"] == "Hera"

    # Verify Markdown content
    md_content = md_path.read_text(encoding="utf-8")
    assert "# AoE2 Match Analysis: sample" in md_content
    assert "Hera" in md_content
    assert "Arabia" in md_content


def test_coaching_export(tmp_path: Path) -> None:
    coaching = CoachingReport(
        replay_name="sample",
        player_name="Hera",
        language="en",
        sections={"Dark Age": ["Good feudal click at 08:00."]},
        raw_response="## Dark Age\n- Good feudal click at 08:00.",
    )
    coach_path = export_coaching(coaching, output_dir=tmp_path, replay_name="sample")
    assert coach_path.exists()
    content = coach_path.read_text(encoding="utf-8")
    assert "Hera" in content
    assert "Good feudal click at 08:00" in content


def test_truncate_payload_under_limit() -> None:
    report = _create_sample_report()
    payload = truncate_payload_for_llm(report, max_chars=50000)
    data = json.loads(payload)
    assert data["target_player"]["player"]["name"] == "Hera"


# ===========================================================================
# 8. Performance Scorer Tests
# ===========================================================================

def test_performance_scores_calculation() -> None:
    from data.models import CastleAgeMetrics, DarkAgeMetrics, FeudalAgeMetrics

    dark_age = DarkAgeMetrics(
        feudal_click_s=600.0,
        feudal_complete_s=730.0,
        estimated_vils_at_click=22,
        loom_time_s=150.0,
        loom_early=False,
        idle_tc_gaps=[],
        total_idle_tc_s=60.0,  # 10% idle
        build_order=[],
        resource_gather_ratios={"food": 0.6, "wood": 0.4},
        tc_distance_flags=[],
    )
    feudal_age = FeudalAgeMetrics(
        castle_click_s=1100.0,
        castle_complete_s=1260.0,
        opening_strategy="scouts",
        early_gold_flag=False,
        first_farm_time_s=650.0,
        total_farms_built=16,
        farm_build_rate=2.2,
        wheelbarrow_time_s=900.0,
        wheelbarrow_vil_count=28,
        tc_gather_point_description="Near TC / Straggler trees (avg distance: 4.2 tiles)",
        military_buildings={"Stable": 1},
    )
    castle_age = CastleAgeMetrics(
        imperial_click_s=1800.0,
        imperial_complete_s=1990.0,
        composition_focus_score=1.0,
        distinct_unit_lines=["Knight line"],
        unit_line_counts={"Knight line": 20},
        production_buildings_added={"Stable": 2, "Town Center": 2},
        blacksmith_upgrades=[
            {"timestamp_s": 1300.0, "action_type": "research", "param": "Iron Casting"},
            {"timestamp_s": 1350.0, "action_type": "research", "param": "Chain Barding Armor"},
        ],
        tc_count=3,
        scattered_composition_flag=False,
    )

    scores = calculate_performance_scores(
        dark_age=dark_age,
        feudal_age=feudal_age,
        castle_age=castle_age,
        game_duration_s=2400.0,
    )

    assert scores.tc_idle_pct == 10.0
    assert scores.tc_uptime_pct == 90.0
    assert scores.eco_efficiency_score >= 85.0
    assert scores.military_value_score >= 80.0
    assert scores.total_military_units == 20
    assert scores.overall_score >= 80.0
    assert scores.overall_grade in ["S", "A", "B", "C", "D"]
    assert "Overall Match Rating" not in scores.overall_rating  # check format like 'A (85.5% - Solid Competitive / 1200-1500 Elo)'
    assert scores.overall_grade in scores.overall_rating


# ===========================================================================
# 9. Civilization Database & Matchup Tests
# ===========================================================================

def test_civ_database_loads_all_civilizations() -> None:
    from data.civ_database import get_civilization, load_civilizations

    db = load_civilizations()
    # AoE2 DE has 45 civilizations
    assert len(db) == 45
    assert "Bulgarians" in db
    assert "Franks" in db
    assert "Britons" in db
    assert "Romans" in db

    bulgarians = get_civilization("bulgarians")
    assert bulgarians is not None
    assert any("Konnik" in u for u in bulgarians["unique_units"])
    assert "NO PALADIN" in bulgarians["tech_restrictions"]


def test_format_matchup_overview() -> None:
    from data.civ_database import format_matchup_overview

    overview = format_matchup_overview(
        target_player_name="DJaystar9083",
        target_player_civ="Bulgarians",
        opponents=[
            {"name": "Kotone", "civilization": "Malay"},
            {"name": "SubjectTMT", "civilization": "Franks"},
        ],
    )

    assert "DJaystar9083" in overview
    assert "BULGARIANS" in overview
    assert "Kotone" in overview
    assert "Malay" in overview
    assert "SubjectTMT" in overview
    assert "Franks" in overview
    assert "NO PALADIN" in overview


def test_build_multi_layer_analysis() -> None:
    from analyzer.multi_layer_analyzer import build_multi_layer_analysis
    report = _create_sample_report()
    tp = report.target_player

    ml = build_multi_layer_analysis(
        metadata=report.metadata,
        player_info=tp.player,
        dark_age=tp.dark_age,
        feudal_age=tp.feudal_age,
        castle_age=tp.castle_age,
        imperial_age=tp.imperial_age,
        scores=tp.scores,
        opponents=report.opponents,
    )

    assert ml is not None
    assert "tc_uptime_pct" in ml.economy.continuity
    assert "food_engine_type" in ml.economy.resource_allocation
    assert "volume_rating" in ml.military.volume_pacing
    assert "army_archetype" in ml.military.composition_synergy
    assert "expected_role_responsibility" in ml.strategy.format_and_role


def test_combat_and_micro_analysis() -> None:
    from analyzer.combat_micro_analyzer import analyze_micro_actions, analyze_units_lost

    raw_inputs = [
        {"timestamp_s": 100.0, "type": "Move"},
        {"timestamp_s": 105.0, "type": "Target", "param": "Archer"},
        {"timestamp_s": 110.0, "type": "Patrol"},
        {"timestamp_s": 120.0, "type": "Garrison"},
        {"timestamp_s": 125.0, "type": "Ungarrison"},
        {"timestamp_s": 130.0, "type": "Stance", "param": "Stand Ground"},
    ]

    micro = analyze_micro_actions(raw_inputs, game_duration_s=600.0)
    assert micro["total_tactical_commands"] == 6
    assert micro["target_commands"] == 1
    assert micro["patrol_commands"] == 1
    assert micro["garrison_commands"] == 1
    assert micro["micro_score"] > 0

    class DummyRow:
        def __init__(self, t: float, o: int):
            from datetime import timedelta
            self.timestamp = timedelta(seconds=t)
            self.total_objects = o

    ts = [
        DummyRow(0.0, 14),
        DummyRow(100.0, 20),
        DummyRow(200.0, 12),  # drop of 8
    ]

    combat = analyze_units_lost({"achievements": {}}, timeseries=ts, total_units_trained=25)
    assert combat["units_lost"] > 0
    assert len(combat["major_engagements"]) == 1
    assert combat["major_engagements"][0]["casualties"] == 8


