"""main.py
=======

Command Line Interface (CLI) entry point for the AoE2 DE Replay-to-Coach pipeline.

Commands:
- `convert`: Parses a .aoe2record binary replay file and exports offline JSON & Markdown reports.
- `coach`: Runs the full pipeline, calling Google Gemini to generate sharp, human-like coaching feedback.

Supports:
- Direct CLI invocation: `python main.py match.aoe2record`
- Drag & Drop: Dragging a .aoe2record file onto `run.bat` or the terminal
- Interactive prompt: Running `python main.py` asks for the replay file path automatically.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from ai.coach_client import call_coach_llm, parse_coaching_response, validate_api_key
from analyzer.age_segmenter import filter_events_by_age, segment_by_age
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
    format_timestamp,
)
from config.settings import AoE2Constants
from data.civ_database import get_civilization
from data.exceptions import (
    AIAnalysisError,
    PlayerNotFoundError,
    ReplayLoadError,
    ReplayParseError,
    UnsupportedPatchError,
)
from data.models import (
    CastleAgeMetrics,
    DarkAgeMetrics,
    FeudalAgeMetrics,
    ImperialAgeMetrics,
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
    truncate_payload_for_llm,
)
from parser.mgz_adapter import (
    extract_player_inputs,
    parse_replay,
)
from parser.replay_loader import open_replay, validate_replay_path

app = typer.Typer(
    name="aoe2coach",
    help="AoE2:DE Replay Telemetry Analyzer and AI Coach Pipeline",
    add_completion=False,
)
console = Console()


def prompt_for_replay_path(prompt_text: Optional[str] = None, lang: str = "nl") -> str:
    """Prompt the user interactively for a replay file path.

    Cleans up surrounding quotes and whitespace added when dragging files into Windows terminals.
    Supports English and Dutch prompts.
    """
    if lang == "en":
        default_prompt = "Please enter the path to your .aoe2record file:"
        tip = "(Tip: You can drag and drop your .aoe2record file directly into this window and press Enter)"
        input_label = "📁 [bold green]File path:[/bold green] "
    else:
        default_prompt = "Voer het pad naar je .aoe2record bestand in:"
        tip = "(Tip: Je kunt het .aoe2record bestand direct in dit venster slepen en op Enter drukken)"
        input_label = "📁 [bold green]Bestandspad:[/bold green] "

    display_prompt = prompt_text if prompt_text else default_prompt
    console.print(f"\n[bold yellow]{display_prompt}[/bold yellow]")
    console.print(f"[dim]{tip}[/dim]")
    raw = console.input(f"\n{input_label}").strip()
    return raw.strip("\"'")


def build_telemetry_report(
    metadata_dict: dict[str, Any],
    target_player_dict: dict[str, Any],
    all_players_data: list[dict[str, Any]],
    uptimes_by_player: dict[int, dict[str, float]],
    gaia_objects: list[dict[str, Any]],
    raw_inputs: list[dict[str, Any]],
    game_duration_s: float,
) -> ParsedReplayReport:
    """Orchestrate all heuristic analyzers and assemble a ParsedReplayReport DTO.

    Guard Clauses:
        - Rejects missing player or metadata.
    """
    if not metadata_dict:
        raise ValueError("metadata_dict cannot be empty.")
    if not target_player_dict:
        raise ValueError("target_player_dict cannot be empty.")

    p_num = target_player_dict["number"]
    p_uptimes = uptimes_by_player.get(p_num, {})

    # Detect water objects in map
    has_water_gaia = detect_water_map_objects(gaia_objects)
    is_water_map = metadata_dict.get("is_water_map", False) or has_water_gaia
    is_hybrid_map = metadata_dict.get("is_hybrid_map", False)

    metadata = MatchMetadata(
        map_name=metadata_dict["map_name"],
        map_size=metadata_dict["map_size"],
        game_duration_s=game_duration_s,
        winner_name=metadata_dict.get("winner_name"),
        is_water_map=is_water_map,
        is_hybrid_map=is_hybrid_map,
        game_version=metadata_dict.get("game_version", "Unknown"),
        save_version=metadata_dict.get("save_version", 0.0),
    )

    target_civ_info = get_civilization(target_player_dict["civilization"])
    civ_bonuses = target_civ_info.get("bonuses", []) if target_civ_info else []
    civ_units = target_civ_info.get("unique_units", []) if target_civ_info else []
    civ_restr = target_civ_info.get("tech_restrictions") if target_civ_info else None

    player_info = PlayerInfo(
        name=target_player_dict["name"],
        civilization=target_player_dict["civilization"],
        color=target_player_dict["color"],
        number=p_num,
        tc_x=target_player_dict.get("tc_x"),
        tc_y=target_player_dict.get("tc_y"),
        eapm=target_player_dict.get("eapm"),
        winner=target_player_dict.get("winner"),
        profile_id=target_player_dict.get("profile_id"),
        civ_bonuses=civ_bonuses,
        civ_unique_units=civ_units,
        civ_tech_restrictions=civ_restr,
    )

    # 1. Age Segmentation
    age_segments = segment_by_age(p_uptimes, game_duration_s)
    events_by_age = filter_events_by_age(raw_inputs, age_segments)

    dark_events = events_by_age.get("Dark Age", [])
    feudal_events = events_by_age.get("Feudal Age", [])
    castle_events = events_by_age.get("Castle Age", [])
    imperial_events = events_by_age.get("Imperial Age", [])

    # Feudal Age click & arrival timestamps
    feudal_uptime = p_uptimes.get("feudal")
    feudal_click_s = (
        round(feudal_uptime - AoE2Constants.FEUDAL_AGE_RESEARCH_TIME_S, 1)
        if feudal_uptime is not None
        else None
    )

    # 2. Dark Age Metrics
    idle_gaps, total_idle_tc = calculate_idle_tc_gaps(
        raw_inputs, feudal_click_s, game_duration_s
    )
    vils_at_click = estimate_vils_at_feudal_click(raw_inputs, feudal_click_s)
    loom_time, loom_early = detect_loom_timing(dark_events, feudal_click_s)
    gather_ratios = calculate_resource_gather_ratios(
        dark_events, 0.0, feudal_uptime or game_duration_s
    )
    tc_distance_flags = check_gather_distances(
        dark_events, player_info.tc_x, player_info.tc_y
    )
    build_order = extract_build_order(dark_events, max_entries=25)

    dark_age_metrics = DarkAgeMetrics(
        feudal_click_s=feudal_click_s,
        feudal_complete_s=feudal_uptime,
        estimated_vils_at_click=vils_at_click,
        loom_time_s=loom_time,
        loom_early=loom_early,
        idle_tc_gaps=idle_gaps,
        total_idle_tc_s=total_idle_tc,
        build_order=build_order,
        resource_gather_ratios=gather_ratios,
        tc_distance_flags=tc_distance_flags,
    )

    # 3. Feudal Age Metrics
    feudal_metrics: FeudalAgeMetrics | None = None
    if feudal_uptime is not None and feudal_uptime < game_duration_s:
        castle_uptime = p_uptimes.get("castle")
        castle_click_s = (
            round(castle_uptime - AoE2Constants.CASTLE_AGE_RESEARCH_TIME_S, 1)
            if castle_uptime is not None
            else None
        )
        opening = detect_opening_strategy(feudal_events, dark_events)
        early_gold = detect_early_gold(
            raw_inputs, opening, feudal_uptime, castle_uptime or game_duration_s
        )
        first_farm, total_farms, farm_rate = detect_farm_timing(
            raw_inputs, feudal_uptime, castle_uptime or game_duration_s
        )
        wb_time, wb_vils = detect_wheelbarrow_timing(raw_inputs)
        tc_gp_desc = check_tc_gather_point(
            raw_inputs,
            player_info.tc_x,
            player_info.tc_y,
            feudal_uptime,
            castle_uptime or game_duration_s,
        )
        mil_bldgs = count_military_buildings(
            raw_inputs, feudal_uptime, castle_uptime or game_duration_s
        )

        feudal_metrics = FeudalAgeMetrics(
            castle_click_s=castle_click_s,
            castle_complete_s=castle_uptime,
            opening_strategy=opening,
            early_gold_flag=early_gold,
            first_farm_time_s=first_farm,
            total_farms_built=total_farms,
            farm_build_rate=farm_rate,
            wheelbarrow_time_s=wb_time,
            wheelbarrow_vil_count=wb_vils,
            tc_gather_point_description=tc_gp_desc,
            military_buildings=mil_bldgs,
        )

    # 4. Castle Age Metrics
    castle_metrics: CastleAgeMetrics | None = None
    castle_uptime = p_uptimes.get("castle")
    if castle_uptime is not None and castle_uptime < game_duration_s:
        imperial_uptime = p_uptimes.get("imperial")
        imperial_click_s = (
            round(imperial_uptime - AoE2Constants.IMPERIAL_AGE_RESEARCH_TIME_S, 1)
            if imperial_uptime is not None
            else None
        )
        focus_score, distinct_lines, line_counts, is_scattered = calculate_composition_focus(
            raw_inputs, castle_uptime, imperial_uptime or game_duration_s
        )
        prod_scaling = count_production_scaling(
            raw_inputs, castle_uptime, (imperial_uptime or game_duration_s)
        )
        bs_upgrades = extract_blacksmith_upgrades(
            raw_inputs, castle_uptime, imperial_uptime or game_duration_s
        )
        extra_tcs = sum(
            1 for ev in raw_inputs
            if "town center" in str(ev.get("param", "")).lower() and "build" in str(ev.get("type", "")).lower()
        )

        castle_metrics = CastleAgeMetrics(
            imperial_click_s=imperial_click_s,
            imperial_complete_s=imperial_uptime,
            composition_focus_score=focus_score,
            distinct_unit_lines=distinct_lines,
            unit_line_counts=line_counts,
            production_buildings_added=prod_scaling,
            blacksmith_upgrades=bs_upgrades,
            tc_count=1 + extra_tcs,
            scattered_composition_flag=is_scattered,
        )

    # 5. Imperial Age Metrics
    imperial_metrics: ImperialAgeMetrics | None = None
    imperial_uptime = p_uptimes.get("imperial")
    if imperial_uptime is not None and imperial_uptime < game_duration_s:
        imp_upgrades = extract_blacksmith_upgrades(
            raw_inputs, imperial_uptime, game_duration_s
        )
        treb_count = sum(
            1 for ev in raw_inputs
            if "trebuchet" in str(ev.get("param", "")).lower() and "queue" in str(ev.get("type", "")).lower()
        )
        imperial_metrics = ImperialAgeMetrics(
            key_upgrades=imp_upgrades,
            trebuchet_count=treb_count,
        )

    # 6. Opponents Summary
    opponents: list[OpponentSummary] = []
    for other_p in all_players_data:
        o_num = other_p["number"]
        if o_num == p_num:
            continue

        o_uptimes = uptimes_by_player.get(o_num, {})
        o_feudal_up = o_uptimes.get("feudal")
        o_castle_up = o_uptimes.get("castle")
        o_imp_up = o_uptimes.get("imperial")

        o_feudal_click = (
            round(o_feudal_up - AoE2Constants.FEUDAL_AGE_RESEARCH_TIME_S, 1)
            if o_feudal_up is not None
            else None
        )
        o_castle_click = (
            round(o_castle_up - AoE2Constants.CASTLE_AGE_RESEARCH_TIME_S, 1)
            if o_castle_up is not None
            else None
        )
        o_imp_click = (
            round(o_imp_up - AoE2Constants.IMPERIAL_AGE_RESEARCH_TIME_S, 1)
            if o_imp_up is not None
            else None
        )

        o_civ_data = get_civilization(other_p["civilization"])
        opponents.append(
            OpponentSummary(
                name=other_p["name"],
                civilization=other_p["civilization"],
                feudal_click_s=o_feudal_click,
                castle_click_s=o_castle_click,
                imperial_click_s=o_imp_click,
                primary_unit_line=None,
                military_building_count=None,
                civ_focus=o_civ_data.get("focus") if o_civ_data else None,
                civ_bonuses=o_civ_data.get("bonuses", []) if o_civ_data else [],
                civ_unique_units=o_civ_data.get("unique_units", []) if o_civ_data else [],
            )
        )

    # 5. Executive Performance Scores
    scores = calculate_performance_scores(
        dark_age=dark_age_metrics,
        feudal_age=feudal_metrics,
        castle_age=castle_metrics,
        imperial_age=imperial_metrics,
        game_duration_s=game_duration_s,
    )

    telemetry = PlayerTelemetry(
        player=player_info,
        dark_age=dark_age_metrics,
        feudal_age=feudal_metrics,
        castle_age=castle_metrics,
        imperial_age=imperial_metrics,
        scores=scores,
    )

    return ParsedReplayReport(
        metadata=metadata,
        target_player=telemetry,
        opponents=opponents,
    )


@app.command()
def convert(
    replay_path: Optional[str] = typer.Argument(
        None,
        help="Path to .aoe2record replay file (optioneel, wordt gevraagd indien leeg)",
    ),
    output_dir: str = typer.Option("output", "--output-dir", "-o", help="Directory for output files"),
) -> None:
    """Parse an .aoe2record file and export offline JSON & Markdown reports. Zero API cost."""
    # Guard Clause: interactive prompt if path is not provided via CLI args
    if not replay_path or not replay_path.strip():
        replay_path = prompt_for_replay_path("Geen bestand opgegeven voor 'convert'.")

    clean_path = replay_path.strip("\"'")
    if not clean_path:
        err_msg = "No file path was entered." if lang == "en" else "Geen bestandspad ingevoerd."
        console.print(f"[bold red]Load Error:[/bold red] {err_msg}")
        raise typer.Exit(code=1)

    try:
        validated_path = validate_replay_path(clean_path)
    except ReplayLoadError as e:
        console.print(f"[bold red]Load Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Parsing replay:[/bold cyan] {validated_path.name}")

    try:
        with open_replay(validated_path) as handle:
            parsed_data = parse_replay(handle, replay_path=str(validated_path))
    except (UnsupportedPatchError, ReplayParseError, ReplayLoadError) as e:
        console.print(f"[bold red]Parser Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    players = parsed_data.get("players", [])
    if not players:
        console.print("[bold red]Error:[/bold red] No players found in replay file.")
        raise typer.Exit(code=1)

    target_player = players[0]
    match_obj = parsed_data.get("match")
    raw_inputs = extract_player_inputs(match_obj, target_player["number"]) if match_obj else []

    report = build_telemetry_report(
        metadata_dict=parsed_data["metadata"],
        target_player_dict=target_player,
        all_players_data=players,
        uptimes_by_player=parsed_data["uptimes"],
        gaia_objects=parsed_data["gaia"],
        raw_inputs=raw_inputs,
        game_duration_s=parsed_data["metadata"]["game_duration_s"],
    )

    stem = validated_path.stem
    json_path = export_json(report, output_dir=output_dir, replay_name=stem)
    md_path = export_markdown(report, output_dir=output_dir, replay_name=stem)

    scores_snippet = ""
    if report.target_player.scores:
        sc = report.target_player.scores
        scores_snippet = (
            f"\n\n[bold yellow]Performance Benchmarks:[/bold yellow]\n"
            f"• TC Uptime (Dark Age): [bold cyan]{sc.tc_uptime_pct}%[/bold cyan] (Idle: {sc.tc_idle_pct}%)\n"
            f"• Economy Efficiency:   [bold cyan]{sc.eco_efficiency_score}%[/bold cyan]\n"
            f"• Military Focus/Value: [bold cyan]{sc.military_value_score}%[/bold cyan] ({sc.total_military_units} units)"
        )

    console.print(
        Panel.fit(
            f"[bold green]Conversion Complete![/bold green]\n\n"
            f"• Analyzed Player: [bold]{target_player['name']}[/bold] ({target_player['civilization']})\n"
            f"• Map: [bold]{report.metadata.map_name}[/bold] ({format_timestamp(report.metadata.game_duration_s)})\n"
            f"• JSON Telemetry: [cyan]{json_path}[/cyan]\n"
            f"• Readable Markdown: [cyan]{md_path}[/cyan]"
            f"{scores_snippet}",
            title="AoE2 Replay Converted",
        )
    )


@app.command()
def coach(
    replay_path: Optional[str] = typer.Argument(
        None,
        help="Path to .aoe2record replay file (optioneel, wordt gevraagd indien leeg)",
    ),
    player: Optional[str] = typer.Option(None, "--player", "-p", help="Target player name to coach"),
    lang: str = typer.Option("nl", "--lang", "-l", help="Output language: nl (Nederlands) of en (Engels)"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-q", help="Optionele vraag of focuspunt voor de AI coach"),
    output_dir: str = typer.Option("output", "--output-dir", "-o", help="Directory for output files"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Gemini model identifier (defaults to .env)"),
) -> None:
    """Run the complete coaching pipeline with Google Gemini AI feedback."""
    # Guard Clause 1: Validate API key before doing expensive parsing
    try:
        validate_api_key()
    except AIAnalysisError as e:
        console.print(f"[bold red]API Key Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    # Guard Clause 2: If no path given in argv, prompt interactively
    if not replay_path or not replay_path.strip():
        prompt_text = (
            "No replay file provided for the AI Coach."
            if lang == "en"
            else "Geen replaybestand opgegeven voor de AI Coach."
        )
        replay_path = prompt_for_replay_path(prompt_text, lang=lang)

    clean_path = replay_path.strip("\"'")
    if not clean_path:
        err_msg = "No file path was entered." if lang == "en" else "Geen bestandspad ingevoerd."
        console.print(f"[bold red]Load Error:[/bold red] {err_msg}")
        raise typer.Exit(code=1)

    # Guard Clause 3: Validate replay path
    try:
        validated_path = validate_replay_path(clean_path)
    except ReplayLoadError as e:
        console.print(f"[bold red]Load Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Parsing replay:[/bold cyan] {validated_path.name}")

    try:
        with open_replay(validated_path) as handle:
            parsed_data = parse_replay(handle, replay_path=str(validated_path))
    except (UnsupportedPatchError, ReplayParseError, ReplayLoadError) as e:
        console.print(f"[bold red]Parser Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    players = parsed_data.get("players", [])
    if not players:
        console.print("[bold red]Error:[/bold red] No players found in replay.")
        raise typer.Exit(code=1)

    # Step 1: Target player selection (interactive if not provided)
    target_player: dict[str, Any] | None = None
    if player:
        matched = [p for p in players if p["name"].lower() == player.lower().strip()]
        if not matched:
            available = [p["name"] for p in players]
            err = PlayerNotFoundError(player, available)
            console.print(f"[bold red]Player Not Found:[/bold red] {err}")
            raise typer.Exit(code=1)
        target_player = matched[0]
    else:
        # Prompt user to choose which player to analyze
        if len(players) == 1:
            target_player = players[0]
        else:
            if lang == "en":
                console.print("\n[bold cyan]Players found in replay:[/bold cyan]")
                for i, p in enumerate(players, start=1):
                    console.print(f"  [{i}] [bold]{p['name']}[/bold] ({p['civilization']})")
                prompt_msg = f"\n👤 [bold yellow]Which player do you want to coach? (number or name, press Enter for {players[0]['name']}): [/bold yellow]"
            else:
                console.print("\n[bold cyan]Spelers gevonden in replay:[/bold cyan]")
                for i, p in enumerate(players, start=1):
                    console.print(f"  [{i}] [bold]{p['name']}[/bold] ({p['civilization']})")
                prompt_msg = f"\n👤 [bold yellow]Welke speler wil je analyseren? (nummer of naam, druk op Enter voor {players[0]['name']}): [/bold yellow]"

            choice = console.input(prompt_msg).strip()
            if not choice:
                target_player = players[0]
            elif choice.isdigit() and 1 <= int(choice) <= len(players):
                target_player = players[int(choice) - 1]
            else:
                matched = [p for p in players if p["name"].lower() == choice.lower()]
                if matched:
                    target_player = matched[0]
                else:
                    matched_part = [p for p in players if choice.lower() in p["name"].lower()]
                    if matched_part:
                        target_player = matched_part[0]
                    else:
                        fallback_msg = (
                            f"[yellow]Player '{choice}' not found. Defaulting to {players[0]['name']}.[/yellow]"
                            if lang == "en"
                            else f"[yellow]Speler '{choice}' niet gevonden. Standaard gekozen voor {players[0]['name']}.[/yellow]"
                        )
                        console.print(fallback_msg)
                        target_player = players[0]

    confirmed_msg = (
        f"Coaching player: [bold green]{target_player['name']}[/bold green] ({target_player['civilization']})"
        if lang == "en"
        else f"Gekozen speler voor analyse: [bold green]{target_player['name']}[/bold green] ({target_player['civilization']})"
    )
    console.print(f"[dim]{confirmed_msg}[/dim]")

    # Step 2: Optional interactive question or focus point for the coach
    user_question = prompt
    if not user_question:
        q_prompt = (
            "\n💬 [bold yellow]Any specific question or focus area for the coach? (optional, press Enter to skip): [/bold yellow]"
            if lang == "en"
            else "\n💬 [bold yellow]Specifieke vraag of focuspunt voor de coach? (optioneel, druk op Enter om over te slaan): [/bold yellow]"
        )
        q = console.input(q_prompt).strip()
        if q:
            user_question = q

    match_obj = parsed_data.get("match")
    raw_inputs = extract_player_inputs(match_obj, target_player["number"]) if match_obj else []

    report = build_telemetry_report(
        metadata_dict=parsed_data["metadata"],
        target_player_dict=target_player,
        all_players_data=players,
        uptimes_by_player=parsed_data["uptimes"],
        gaia_objects=parsed_data["gaia"],
        raw_inputs=raw_inputs,
        game_duration_s=parsed_data["metadata"]["game_duration_s"],
    )

    stem = validated_path.stem
    # Save offline reports first
    export_json(report, output_dir=output_dir, replay_name=stem)
    export_markdown(report, output_dir=output_dir, replay_name=stem)

    if lang == "en":
        console.print(f"[bold cyan]Consulting AI Coach (EN) via Gemini...[/bold cyan]")
    else:
        console.print(f"[bold cyan]AI Coach raadplegen ({lang.upper()}) via Gemini...[/bold cyan]")
    payload_json = truncate_payload_for_llm(report)

    try:
        raw_coaching = call_coach_llm(
            report_json=payload_json,
            language=lang,
            model=model,
            target_civ=target_player.get("civilization"),
            user_question=user_question,
        )
    except AIAnalysisError as e:
        console.print(f"[bold red]AI Coaching Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    coaching_report = parse_coaching_response(
        raw_response=raw_coaching,
        player_name=target_player["name"],
        replay_name=stem,
        language=lang,
    )

    coaching_path = export_coaching(coaching_report, output_dir=output_dir, replay_name=stem)

    if lang == "en":
        panel_content = (
            f"[bold green]Coaching Analysis Successfully Generated![/bold green]\n"
            f"Saved to: [cyan]{coaching_path}[/cyan]"
        )
    else:
        panel_content = (
            f"[bold green]Coaching Analyse Succesvol Gegenereerd![/bold green]\n"
            f"Opgeslagen in: [cyan]{coaching_path}[/cyan]"
        )

    console.print(
        Panel.fit(
            panel_content,
            title="AoE2 AI Coach",
        )
    )

    # Render markdown in terminal
    console.print(Markdown(raw_coaching))

    # Render match performance scores panel standard under output
    if report.target_player.scores:
        sc = report.target_player.scores
        idle_s = report.target_player.dark_age.total_idle_tc_s
        if lang == "en":
            scores_content = (
                f"• [bold]Town Center Uptime (Dark Age):[/bold]  [bold cyan]{sc.tc_uptime_pct}%[/bold cyan] "
                f"([dim]Idle: {sc.tc_idle_pct}% | {format_timestamp(idle_s)} min[/dim])\n"
                f"• [bold]Economy Efficiency Score:[/bold]       [bold cyan]{sc.eco_efficiency_score}%[/bold cyan]\n"
                f"• [bold]Military Value & Focus Score:[/bold]   [bold cyan]{sc.military_value_score}%[/bold cyan] "
                f"([dim]{sc.total_military_units} units produced[/dim])"
            )
            scores_title = "📊 Match Performance Benchmarks"
        else:
            scores_content = (
                f"• [bold]Town Center Uptime (Dark Age):[/bold]  [bold cyan]{sc.tc_uptime_pct}%[/bold cyan] "
                f"([dim]Idle: {sc.tc_idle_pct}% | {format_timestamp(idle_s)} min[/dim])\n"
                f"• [bold]Economie Efficiëntie Score:[/bold]     [bold cyan]{sc.eco_efficiency_score}%[/bold cyan]\n"
                f"• [bold]Militaire Waarde & Focus:[/bold]        [bold cyan]{sc.military_value_score}%[/bold cyan] "
                f"([dim]{sc.total_military_units} eenheden geproduceerd[/dim])"
            )
            scores_title = "📊 Wedstrijd Prestatie Scores"

        console.print(Panel(scores_content, title=scores_title, border_style="cyan"))


def main() -> None:
    """Smart CLI launcher that handles drag-and-drop, direct file args, and default interactive runs."""
    # Scenario A: User dragged a file onto run.bat or passed it directly:
    # e.g.: `python main.py "match.aoe2record"` -> route directly to `coach`
    if len(sys.argv) == 2 and sys.argv[1] not in ["convert", "coach", "--help", "-h"]:
        sys.argv.insert(1, "coach")
    # Scenario B: User simply ran `python main.py` without any arguments
    elif len(sys.argv) == 1:
        sys.argv.append("coach")

    app()


if __name__ == "__main__":
    main()
