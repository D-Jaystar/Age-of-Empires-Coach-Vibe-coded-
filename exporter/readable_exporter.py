"""exporter/readable_exporter.py
=============================

Converts the parsed replay data transfer object (ParsedReplayReport) into:
1. Structured, pretty-printed JSON (<name>_parsed.json)
2. Comprehensive, human-readable Markdown summary & build order table (<name>_readable.md)
3. AI coaching report Markdown (<name>_coaching.md)
4. Safe, truncated payload serialization for LLM ingestion
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from analyzer.spatial_heuristics import format_timestamp
from data.models import CoachingReport, ParsedReplayReport


def format_duration(seconds: float | None) -> str:
    """Format duration in seconds into MM:SS or HH:MM:SS format."""
    return format_timestamp(seconds)


def export_json(
    report: ParsedReplayReport,
    output_dir: str | Path,
    replay_name: str,
) -> Path:
    """Serialize the ParsedReplayReport to formatted JSON.

    Guard Clauses:
        - If report is None, raises ValueError.
        - Ensures output directory exists.

    Args:
        report: The full parsed telemetry report DTO.
        output_dir: Target folder to store output files.
        replay_name: Base stem name of the replay.

    Returns:
        Path: Path to the generated JSON file.
    """
    if report is None:
        raise ValueError("ParsedReplayReport cannot be None.")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    target_file = out_path / f"{replay_name}_parsed.json"
    data = report.model_dump(mode="json")

    with open(target_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return target_file


def export_markdown(
    report: ParsedReplayReport,
    output_dir: str | Path,
    replay_name: str,
) -> Path:
    """Generate a clean, readable Markdown summary and build order table.

    Allows players to inspect their exact game statistics and timings offline
    without calling the AI model.

    Guard Clauses:
        - If report is None, raises ValueError.
        - Ensures output directory exists.

    Returns:
        Path: Path to the generated Markdown file.
    """
    if report is None:
        raise ValueError("ParsedReplayReport cannot be None.")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    target_file = out_path / f"{replay_name}_readable.md"
    meta = report.metadata
    tp = report.target_player
    p_info = tp.player

    md_lines: list[str] = [
        f"# AoE2 Match Analysis: {replay_name}",
        "",
        "## Match Overview",
        "",
        f"- **Map:** {meta.map_name} ({meta.map_size})",
        f"- **Type:** {'Water Map' if meta.is_water_map else 'Hybrid Map' if meta.is_hybrid_map else 'Land Map'}",
        f"- **Duration:** {format_duration(meta.game_duration_s)} ({int(meta.game_duration_s)}s)",
        f"- **Winner:** {meta.winner_name or 'Undetermined'}",
        f"- **Analyzed Player:** **{p_info.name}** ({p_info.civilization}) - Slot #{p_info.number} [{p_info.color}]",
    ]

    if p_info.eapm is not None:
        md_lines.append(f"- **eAPM:** {p_info.eapm}")

    if p_info.civ_bonuses:
        md_lines.append(f"- **Civ Bonuses:** {'; '.join(p_info.civ_bonuses[:2])}")
    if p_info.civ_unique_units:
        md_lines.append(f"- **Unique Units:** {', '.join(p_info.civ_unique_units)}")
    if p_info.civ_tech_restrictions:
        md_lines.append(f"- **Tech Tree Limits:** {p_info.civ_tech_restrictions}")

    # Executive Performance Scores
    if tp.scores:
        sc = tp.scores
        md_lines.extend([
            "",
            "---",
            "## 📊 Executive Performance Scores",
            "",
            "| Metric | Score | Details |",
            "| :--- | :---: | :--- |",
            f"| **Town Center Uptime (Dark Age)** | **{sc.tc_uptime_pct}%** | Total Idle: {tp.dark_age.total_idle_tc_s:.1f}s ({sc.tc_idle_pct}% idle) |",
            f"| **Economy Efficiency Score** | **{sc.eco_efficiency_score}%** | Benchmark based on TC consistency, farming engine, drop-off distance |",
            f"| **Military Value & Focus Score** | **{sc.military_value_score}%** | Total units: {sc.total_military_units}, composition focus & upgrades |",
        ])

    # 1. Dark Age
    da = tp.dark_age
    md_lines.extend([
        "",
        "---",
        "## 🏰 Dark Age Telemetry",
        "",
        f"- **Feudal Click Time:** {format_duration(da.feudal_click_s)} ({da.feudal_click_s or 'N/A'}s)",
        f"- **Feudal Arrival Time:** {format_duration(da.feudal_complete_s)} ({da.feudal_complete_s or 'N/A'}s)",
        f"- **Estimated Population at Click:** {da.estimated_vils_at_click or 'Unknown'} villagers",
        f"- **Loom Researched:** {format_duration(da.loom_time_s)} ({'⚠️ Early Loom' if da.loom_early else 'Standard timing'})" if da.loom_time_s else "- **Loom Researched:** None",
        f"- **Total TC Idle Time:** **{da.total_idle_tc_s:.1f}s**",
    ])

    if da.resource_gather_ratios:
        ratios_str = ", ".join(f"{res.capitalize()}: {int(val * 100)}%" for res, val in da.resource_gather_ratios.items())
        md_lines.append(f"- **Resource Distribution:** {ratios_str}")

    if da.idle_tc_gaps:
        md_lines.extend([
            "",
            "### Town Center Idle Gaps (>30s)",
            "",
            "| Start | End | Duration | Context |",
            "| :---: | :---: | :---: | :--- |",
        ])
        for gap in da.idle_tc_gaps:
            ctx = f"⚠️ *{gap.context}*" if gap.context else "Queue gap"
            md_lines.append(f"| {format_duration(gap.start_s)} | {format_duration(gap.end_s)} | {gap.duration_s:.1f}s | {ctx} |")

    if da.tc_distance_flags:
        md_lines.extend(["", "### Spatial / Micro Inefficiencies"])
        for flag in da.tc_distance_flags:
            md_lines.append(f"- ⚠️ {flag}")

    # 2. Feudal Age
    if tp.feudal_age:
        fa = tp.feudal_age
        md_lines.extend([
            "",
            "---",
            "## 🏹 Feudal Age Telemetry",
            "",
            f"- **Opening Strategy:** **{fa.opening_strategy.upper()}**",
            f"- **Castle Age Click Time:** {format_duration(fa.castle_click_s)} ({fa.castle_click_s or 'N/A'}s)",
            f"- **Castle Age Arrival:** {format_duration(fa.castle_complete_s)} ({fa.castle_complete_s or 'N/A'}s)",
            f"- **Early Gold Mined:** {'⚠️ Yes (inefficient for pure scouts)' if fa.early_gold_flag else 'No'}",
            f"- **First Farm Built:** {format_duration(fa.first_farm_time_s)} | **Total Farms:** {fa.total_farms_built} ({fa.farm_build_rate or 0:.1f} farms/min)",
            f"- **Wheelbarrow:** {format_duration(fa.wheelbarrow_time_s)} (at ~{fa.wheelbarrow_vil_count or 'N/A'} vils)" if fa.wheelbarrow_time_s else "- **Wheelbarrow:** Not researched in Feudal",
        ])
        if fa.tc_gather_point_description:
            md_lines.append(f"- **TC Gather Point:** {fa.tc_gather_point_description}")
        if fa.military_buildings:
            bldgs = ", ".join(f"{b}: {c}" for b, c in fa.military_buildings.items())
            md_lines.append(f"- **Military Buildings Constructed:** {bldgs}")

    # 3. Castle Age
    if tp.castle_age:
        ca = tp.castle_age
        md_lines.extend([
            "",
            "---",
            "## ⚔️ Castle Age Telemetry",
            "",
            f"- **Imperial Click Time:** {format_duration(ca.imperial_click_s)}" if ca.imperial_click_s else "- **Imperial Click Time:** None",
            f"- **Composition Focus Score:** {ca.composition_focus_score or 1.0:.2f} / 1.0 {'⚠️ Scattered composition!' if ca.scattered_composition_flag else '✅ Focused'}",
            f"- **Total Town Centers:** {ca.tc_count}",
        ])
        if ca.unit_line_counts:
            units = ", ".join(f"{u}: {c}" for u, c in ca.unit_line_counts.items())
            md_lines.append(f"- **Units Trained:** {units}")
        if ca.production_buildings_added:
            prod = ", ".join(f"{b}: {c}" for b, c in ca.production_buildings_added.items())
            md_lines.append(f"- **Production Added:** {prod}")
        if ca.blacksmith_upgrades:
            techs = ", ".join(f"{u.param} ({format_duration(u.timestamp_s)})" for u in ca.blacksmith_upgrades)
            md_lines.append(f"- **Blacksmith & Military Techs:** {techs}")

    # 4. Opponents Benchmark
    if report.opponents:
        md_lines.extend([
            "",
            "---",
            "## 🛡️ Opponent Benchmark & Matchup",
            "",
            "| Opponent | Civ | Focus | Feudal Click | Castle Click | Unique Units |",
            "| :--- | :--- | :--- | :---: | :---: | :--- |",
        ])
        for opp in report.opponents:
            uu_str = ", ".join(opp.civ_unique_units) if opp.civ_unique_units else "N/A"
            focus_str = opp.civ_focus or "Versatile"
            md_lines.append(
                f"| {opp.name or 'Opponent'} | {opp.civilization} | {focus_str} | "
                f"{format_duration(opp.feudal_click_s)} | {format_duration(opp.castle_click_s)} | "
                f"{uu_str} |"
            )

    # 5. Chronological Build Order (First 25)
    if da.build_order:
        md_lines.extend([
            "",
            "---",
            "## 📋 Initial Build Order (First 25 Actions)",
            "",
            "| # | Time | Action Type | Details | Position |",
            "| :---: | :---: | :---: | :--- | :---: |",
        ])
        for idx, item in enumerate(da.build_order, 1):
            pos = f"({item.position_x:.0f}, {item.position_y:.0f})" if item.position_x is not None else "-"
            md_lines.append(f"| {idx} | {format_duration(item.timestamp_s)} | {item.action_type} | {item.param or '-'} | {pos} |")

    md_lines.append("")

    with open(target_file, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return target_file


def export_coaching(
    coaching: CoachingReport,
    output_dir: str | Path,
    replay_name: str,
) -> Path:
    """Save the AI coaching feedback as a Markdown document.

    Guard Clauses:
        - If coaching is None, raises ValueError.
        - Ensures output directory exists.
    """
    if coaching is None:
        raise ValueError("CoachingReport cannot be None.")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    target_file = out_path / f"{replay_name}_coaching.md"

    header = [
        f"# AoE2 AI Coach: {coaching.player_name}",
        f"**Replay:** `{coaching.replay_name}` | **Language:** `{coaching.language.upper()}`",
        "",
        "---",
        "",
    ]

    content = "\n".join(header) + coaching.raw_response.strip() + "\n"

    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)

    return target_file


def truncate_payload_for_llm(
    report: ParsedReplayReport,
    max_chars: int = 100000,
) -> str:
    """Serialize the telemetry report into compact JSON while guarding against context overflows.

    If the serialized payload exceeds `max_chars`, it trims non-essential verbose fields
    such as raw coordinates and long build-order tails while preserving all core timing
    and strategy metrics.

    Guard Clauses:
        - If report is None, raises ValueError.
        - max_chars must be >= 1000.
    """
    if report is None:
        raise ValueError("ParsedReplayReport cannot be None.")
    if max_chars < 1000:
        raise ValueError("max_chars must be at least 1000.")

    raw_dict = report.model_dump(mode="json")
    json_str = json.dumps(raw_dict, ensure_ascii=False)

    if len(json_str) <= max_chars:
        return json_str

    # Prune build order to first 15 entries
    da = raw_dict.get("target_player", {}).get("dark_age", {})
    if "build_order" in da and len(da["build_order"]) > 15:
        da["build_order"] = da["build_order"][:15]

    # Remove position details from build order
    for entry in da.get("build_order", []):
        entry.pop("position_x", None)
        entry.pop("position_y", None)

    # Prune blacksmith upgrade coordinates
    ca = raw_dict.get("target_player", {}).get("castle_age", {})
    if ca and "blacksmith_upgrades" in ca:
        for entry in ca["blacksmith_upgrades"]:
            entry.pop("position_x", None)
            entry.pop("position_y", None)

    json_str = json.dumps(raw_dict, ensure_ascii=False)
    if len(json_str) > max_chars:
        # Hard truncate build order if still too large
        da["build_order"] = []
        json_str = json.dumps(raw_dict, ensure_ascii=False)

    return json_str
