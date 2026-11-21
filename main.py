"""main.py - CLI entry point for AoE2 DE Replay-to-Coach pipeline."""

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
    extract_military_units,
)
from analyzer.multi_layer_analyzer import build_multi_layer_analysis
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
    BuildOrderEntry,
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
from parser.mgz_adapter import extract_player_inputs, parse_replay
from parser.replay_loader import open_replay, validate_replay_path

app = typer.Typer(name="aoe2coach", help="AoE2:DE Replay Telemetry Analyzer and AI Coach", add_completion=False)
console = Console()


def prompt_for_replay_path(prompt_text: Optional[str] = None, lang: str = "nl") -> str:
    """Prompt the user interactively for a replay file path."""
    if lang == "en":
        msg = prompt_text or "Please enter the path to your .aoe2record file:"
        tip = "(Tip: You can drag and drop your .aoe2record file directly into this window and press Enter)"
        lbl = "📁 [bold green]File path:[/bold green] "
    else:
        msg = prompt_text or "Voer het pad naar je .aoe2record bestand in:"
        tip = "(Tip: Je kunt het .aoe2record bestand direct in dit venster slepen en op Enter drukken)"
        lbl = "📁 [bold green]Bestandspad:[/bold green] "

    console.print(f"\n[bold yellow]{msg}[/bold yellow]\n[dim]{tip}[/dim]")
    return console.input(f"\n{lbl}").strip().strip("\"'")


def _load_and_parse_match(raw_path: str, lang: str = "nl") -> tuple[dict[str, Any], Path]:
    """Helper to validate path and parse replay, exiting gracefully on errors."""
    clean = raw_path.strip().strip("\"'")
    if not clean:
        err = "No file path was entered." if lang == "en" else "Geen bestandspad ingevoerd."
        console.print(f"[bold red]Load Error:[/bold red] {err}")
        raise typer.Exit(code=1)

    try:
        val_path = validate_replay_path(clean)
    except ReplayLoadError as e:
        console.print(f"[bold red]Load Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Parsing replay:[/bold cyan] {val_path.name}")
    try:
        with open_replay(val_path) as handle:
            data = parse_replay(handle, replay_path=str(val_path))
    except (UnsupportedPatchError, ReplayParseError, ReplayLoadError) as e:
        console.print(f"[bold red]Parser Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not data.get("players"):
        console.print("[bold red]Error:[/bold red] No players found in replay.")
        raise typer.Exit(code=1)

    return data, val_path


def _select_target_player(
    players: list[dict[str, Any]],
    player_arg: str | None,
    interactive: bool = True,
    lang: str = "nl",
) -> dict[str, Any]:
    """Select the coached player, either from CLI argument or interactive prompt."""
    if player_arg:
        matched = [p for p in players if p["name"].lower() == player_arg.lower().strip()]
        if not matched:
            err = PlayerNotFoundError(player_arg, [p["name"] for p in players])
            console.print(f"[bold red]Player Not Found:[/bold red] {err}")
            raise typer.Exit(code=1)
        return matched[0]

    if not interactive or len(players) == 1:
        return players[0]

    header = "\n[bold cyan]Players found in replay:[/bold cyan]" if lang == "en" else "\n[bold cyan]Spelers gevonden in replay:[/bold cyan]"
    prompt_msg = (
        f"\n👤 [bold yellow]Which player do you want to coach? (number or name, press Enter for {players[0]['name']}): [/bold yellow]"
        if lang == "en"
        else f"\n👤 [bold yellow]Welke speler wil je analyseren? (nummer of naam, druk op Enter voor {players[0]['name']}): [/bold yellow]"
    )

    console.print(header)
    for i, p in enumerate(players, 1):
        console.print(f"  [{i}] [bold]{p['name']}[/bold] ({p['civilization']})")

    choice = console.input(prompt_msg).strip()
    if not choice:
        target = players[0]
    elif choice.isdigit() and 1 <= int(choice) <= len(players):
        target = players[int(choice) - 1]
    else:
        matched = [p for p in players if p["name"].lower() == choice.lower()] or [
            p for p in players if choice.lower() in p["name"].lower()
        ]
        if matched:
            target = matched[0]
        else:
            fb = f"Player '{choice}' not found. Defaulting to {players[0]['name']}." if lang == "en" else f"Speler '{choice}' niet gevonden. Gekozen voor {players[0]['name']}."
            console.print(f"[yellow]{fb}[/yellow]")
            target = players[0]

    ack = f"Coaching player: [bold green]{target['name']}[/bold green] ({target['civilization']})" if lang == "en" else f"Gekozen speler voor analyse: [bold green]{target['name']}[/bold green] ({target['civilization']})"
    console.print(f"[dim]{ack}[/dim]")
    return target


def _prompt_gamemode(detected_mode: str, interactive: bool = True, lang: str = "nl") -> str:
    """Prompt user for gamemode, defaulting to detected value from replay."""
    if not interactive:
        return detected_mode

    prompt_msg = (
        f"\n🎮 [bold yellow]Which game mode did you play? [1] 1v1 Random Map  [2] Team Game  [3] Empire Wars  [4] Arena / Closed map (Enter for '{detected_mode}'): [/bold yellow]"
        if lang == "en"
        else f"\n🎮 [bold yellow]Welke gamemode speelde je? [1] 1v1 Random Map  [2] Team Game  [3] Empire Wars  [4] Arena / Closed map (Enter voor '{detected_mode}'): [/bold yellow]"
    )
    ans = console.input(prompt_msg).strip()
    mapping = {
        "1": "1v1 Random Map",
        "2": "Team Game",
        "3": "Empire Wars",
        "4": "Arena / Closed map",
    }
    return mapping.get(ans, ans if ans else detected_mode)


def _prompt_map_position(default_pos: str, is_team_game: bool = False, interactive: bool = True, lang: str = "nl") -> str:
    """Prompt user for their map position (Pocket vs Flank vs Solo)."""
    if not interactive:
        return default_pos

    prompt_msg = (
        f"\n🗺️ [bold yellow]What was your map position? [1] Flank  [2] Pocket  [3] Solo (1v1) (Enter for '{default_pos}'): [/bold yellow]"
        if lang == "en"
        else f"\n🗺️ [bold yellow]Wat was je positie op de kaart? [1] Flank  [2] Pocket  [3] Solo (1v1) (Enter voor '{default_pos}'): [/bold yellow]"
    )
    ans = console.input(prompt_msg).strip()
    mapping = {
        "1": "Flank",
        "2": "Pocket",
        "3": "Solo (1v1)",
    }
    return mapping.get(ans, ans if ans else default_pos)


def build_telemetry_report(
    metadata_dict: dict[str, Any],
    target_player_dict: dict[str, Any],
    all_players_data: list[dict[str, Any]],
    uptimes_by_player: dict[int, dict[str, float]],
    gaia_objects: list[dict[str, Any]],
    raw_inputs: list[dict[str, Any]],
    game_duration_s: float,
    gamemode: str | None = None,
    map_position: str | None = None,
) -> ParsedReplayReport:
    """Orchestrate all heuristic analyzers and assemble a ParsedReplayReport DTO."""
    p_num = target_player_dict["number"]
    p_uptimes = uptimes_by_player.get(p_num, {})

    is_water = metadata_dict.get("is_water_map", False) or detect_water_map_objects(gaia_objects)
    detected_gmode = gamemode or metadata_dict.get("gamemode", "Random Map")
    metadata = MatchMetadata(
        map_name=metadata_dict["map_name"],
        map_size=metadata_dict["map_size"],
        game_duration_s=game_duration_s,
        winner_name=metadata_dict.get("winner_name"),
        is_water_map=is_water,
        is_hybrid_map=metadata_dict.get("is_hybrid_map", False),
        game_version=metadata_dict.get("game_version", "Unknown"),
        save_version=metadata_dict.get("save_version", 0.0),
        gamemode=detected_gmode,
        diplomacy=metadata_dict.get("diplomacy"),
        map_position=map_position,
    )

    tc_info = get_civilization(target_player_dict["civilization"]) or {}
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
        civ_bonuses=tc_info.get("bonuses", []),
        civ_unique_units=tc_info.get("unique_units", []),
        civ_tech_restrictions=tc_info.get("tech_restrictions"),
    )

    # 1. Dark Age
    age_segments = segment_by_age(p_uptimes, game_duration_s)
    events_by_age = filter_events_by_age(raw_inputs, age_segments)
    dark_events = events_by_age.get("Dark Age", [])

    feudal_up = p_uptimes.get("feudal")
    feudal_click_s = round(feudal_up - AoE2Constants.FEUDAL_AGE_RESEARCH_TIME_S, 1) if feudal_up else None
    idle_gaps, total_idle_tc = calculate_idle_tc_gaps(raw_inputs, feudal_click_s, game_duration_s)

    dark_metrics = DarkAgeMetrics(
        feudal_click_s=feudal_click_s,
        feudal_complete_s=feudal_up,
        estimated_vils_at_click=estimate_vils_at_feudal_click(raw_inputs, feudal_click_s),
        loom_time_s=detect_loom_timing(dark_events, feudal_click_s)[0],
        loom_early=detect_loom_timing(dark_events, feudal_click_s)[1],
        idle_tc_gaps=idle_gaps,
        total_idle_tc_s=total_idle_tc,
        build_order=extract_build_order(dark_events, max_entries=25),
        resource_gather_ratios=calculate_resource_gather_ratios(dark_events, 0.0, feudal_up or game_duration_s),
        tc_distance_flags=check_gather_distances(dark_events, player_info.tc_x, player_info.tc_y),
    )

    # 2. Feudal Age
    feudal_metrics: FeudalAgeMetrics | None = None
    if feudal_up and feudal_up < game_duration_s:
        castle_up = p_uptimes.get("castle")
        c_click = round(castle_up - AoE2Constants.CASTLE_AGE_RESEARCH_TIME_S, 1) if castle_up else None
        feudal_events = events_by_age.get("Feudal Age", [])
        opening = detect_opening_strategy(feudal_events, dark_events)
        f_farm, tot_farms, f_rate = detect_farm_timing(raw_inputs, feudal_up, castle_up or game_duration_s)
        wb_time, wb_vils = detect_wheelbarrow_timing(raw_inputs)
        feud_mil_count, feud_mil_lines = extract_military_units(raw_inputs, feudal_up, castle_up or game_duration_s)

        feudal_metrics = FeudalAgeMetrics(
            castle_click_s=c_click,
            castle_complete_s=castle_up,
            opening_strategy=opening,
            early_gold_flag=detect_early_gold(raw_inputs, opening, feudal_up, castle_up or game_duration_s),
            first_farm_time_s=f_farm,
            total_farms_built=tot_farms,
            farm_build_rate=f_rate,
            wheelbarrow_time_s=wb_time,
            wheelbarrow_vil_count=wb_vils,
            tc_gather_point_description=check_tc_gather_point(raw_inputs, player_info.tc_x, player_info.tc_y, feudal_up, castle_up or game_duration_s),
            military_buildings=count_military_buildings(raw_inputs, feudal_up, castle_up or game_duration_s),
            military_units_trained=feud_mil_count,
            unit_line_counts=feud_mil_lines,
        )

    # 3. Castle & Imperial Age
    castle_metrics: CastleAgeMetrics | None = None
    imperial_metrics: ImperialAgeMetrics | None = None
    castle_up = p_uptimes.get("castle")

    if castle_up and castle_up < game_duration_s:
        imp_up = p_uptimes.get("imperial")
        i_click = round(imp_up - AoE2Constants.IMPERIAL_AGE_RESEARCH_TIME_S, 1) if imp_up else None
        score, lines, counts, is_scattered = calculate_composition_focus(raw_inputs, castle_up, imp_up or game_duration_s)
        prod_scaling = count_production_scaling(raw_inputs, castle_up, imp_up or game_duration_s)
        tc_count = 1 + prod_scaling.get("Town Center", 0)
        castle_mil_count = sum(counts.values())

        castle_metrics = CastleAgeMetrics(
            imperial_click_s=i_click,
            imperial_complete_s=imp_up,
            composition_focus_score=score,
            distinct_unit_lines=lines,
            unit_line_counts=counts,
            military_units_trained=castle_mil_count,
            production_buildings_added=prod_scaling,
            blacksmith_upgrades=extract_blacksmith_upgrades(raw_inputs, castle_up, imp_up or game_duration_s),
            tc_count=tc_count,
            scattered_composition_flag=is_scattered,
        )

        if imp_up and imp_up < game_duration_s:
            imp_events = events_by_age.get("Imperial Age", [])
            key_upgrades = [
                BuildOrderEntry(timestamp_s=float(ev.get("timestamp_s", 0.0)), action_type=str(ev.get("type", "research")), param=ev.get("param"))
                for ev in imp_events if str(ev.get("type", "")).lower() == "research"
            ]
            trebs = sum(1 for ev in imp_events if "trebuchet" in str(ev.get("param", "")).lower())
            imp_mil_count, imp_mil_lines = extract_military_units(raw_inputs, imp_up, game_duration_s)
            imperial_metrics = ImperialAgeMetrics(
                key_upgrades=key_upgrades,
                trebuchet_count=trebs,
                military_units_trained=imp_mil_count,
                unit_line_counts=imp_mil_lines,
            )

    # 4. Opponents summary
    opponents: list[OpponentSummary] = []
    for op in all_players_data:
        if op["number"] == p_num:
            continue
        o_up = uptimes_by_player.get(op["number"], {})
        o_f = o_up.get("feudal")
        o_c = o_up.get("castle")
        o_i = o_up.get("imperial")
        c_info = get_civilization(op["civilization"]) or {}

        opponents.append(
            OpponentSummary(
                name=op["name"],
                civilization=op["civilization"],
                feudal_click_s=round(o_f - AoE2Constants.FEUDAL_AGE_RESEARCH_TIME_S, 1) if o_f else None,
                castle_click_s=round(o_c - AoE2Constants.CASTLE_AGE_RESEARCH_TIME_S, 1) if o_c else None,
                imperial_click_s=round(o_i - AoE2Constants.IMPERIAL_AGE_RESEARCH_TIME_S, 1) if o_i else None,
                civ_focus=c_info.get("focus"),
                civ_bonuses=c_info.get("bonuses", []),
                civ_unique_units=c_info.get("unique_units", []),
            )
        )

    scores = calculate_performance_scores(dark_metrics, feudal_metrics, castle_metrics, imperial_metrics, game_duration_s)
    multi_layer = build_multi_layer_analysis(
        metadata=metadata,
        player_info=player_info,
        dark_age=dark_metrics,
        feudal_age=feudal_metrics,
        castle_age=castle_metrics,
        imperial_age=imperial_metrics,
        scores=scores,
        opponents=opponents,
    )
    telemetry = PlayerTelemetry(
        player=player_info,
        dark_age=dark_metrics,
        feudal_age=feudal_metrics,
        castle_age=castle_metrics,
        imperial_age=imperial_metrics,
        scores=scores,
        multi_layer=multi_layer,
    )

    return ParsedReplayReport(metadata=metadata, target_player=telemetry, opponents=opponents)


@app.command()
def convert(
    replay_path: Optional[str] = typer.Argument(None, help="Path to .aoe2record replay file"),
    output_dir: str = typer.Option("output", "--output-dir", "-o", help="Output directory"),
) -> None:
    """Parse an .aoe2record file and export offline JSON & Markdown reports. Zero API cost."""
    if not replay_path or not replay_path.strip():
        replay_path = prompt_for_replay_path("Geen bestand opgegeven voor 'convert'.")

    parsed_data, val_path = _load_and_parse_match(replay_path)
    target_player = parsed_data["players"][0]
    match_obj = parsed_data.get("match")
    raw_inputs = extract_player_inputs(match_obj, target_player["number"]) if match_obj else []

    report = build_telemetry_report(
        parsed_data["metadata"], target_player, parsed_data["players"],
        parsed_data["uptimes"], parsed_data["gaia"], raw_inputs, parsed_data["metadata"]["game_duration_s"],
    )

    stem = val_path.stem
    json_path = export_json(report, output_dir, stem)
    md_path = export_markdown(report, output_dir, stem)

    sc = report.target_player.scores
    by_age_str = ", ".join(f"{age.split()[0]}: {cnt}" for age, cnt in sc.military_by_age.items()) if sc and sc.military_by_age else (f"{sc.total_military_units}" if sc else "")
    top_lines = ", ".join(f"{line} ({cnt})" for line, cnt in list(sc.top_military_lines.items())[:3]) if sc else ""
    lines_str = f"\n  ↳ Top Lines: {top_lines}" if top_lines else ""
    sc_str = (
        f"\n\n[bold yellow]Performance Benchmarks:[/bold yellow]\n"
        f"• TC Uptime (Dark Age): [bold cyan]{sc.tc_uptime_pct}%[/bold cyan] (Idle: {sc.tc_idle_pct}%)\n"
        f"• Economy Efficiency:   [bold cyan]{sc.eco_efficiency_score}%[/bold cyan]\n"
        f"• Military Focus/Value: [bold cyan]{sc.military_value_score}%[/bold cyan] ({sc.total_military_units} units: {by_age_str}){lines_str}"
    ) if sc else ""

    console.print(
        Panel.fit(
            f"[bold green]Conversion Complete![/bold green]\n\n"
            f"• Analyzed Player: [bold]{target_player['name']}[/bold] ({target_player['civilization']})\n"
            f"• Map: [bold]{report.metadata.map_name}[/bold] ({format_timestamp(report.metadata.game_duration_s)})\n"
            f"• JSON Telemetry: [cyan]{json_path}[/cyan]\n"
            f"• Readable Markdown: [cyan]{md_path}[/cyan]{sc_str}",
            title="AoE2 Replay Converted",
        )
    )


@app.command()
def coach(
    replay_path: Optional[str] = typer.Argument(None, help="Path to .aoe2record replay file"),
    player: Optional[str] = typer.Option(None, "--player", "-p", help="Target player name"),
    gamemode: Optional[str] = typer.Option(None, "--gamemode", "-g", help="Game mode (e.g. '1v1 Random Map', 'Team Game', 'Arena')"),
    position: Optional[str] = typer.Option(None, "--position", "--pos", help="Map position ('Flank', 'Pocket', 'Solo (1v1)')"),
    lang: str = typer.Option("nl", "--lang", "-l", help="Language: 'nl' or 'en'"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-q", help="Optional player question or focus point"),
    output_dir: str = typer.Option("output", "--output-dir", "-o", help="Output directory"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Gemini model"),
) -> None:
    """Run the complete coaching pipeline with Google Gemini AI feedback."""
    try:
        validate_api_key()
    except AIAnalysisError as e:
        console.print(f"[bold red]API Key Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    if not replay_path or not replay_path.strip():
        msg = "No replay file provided for the AI Coach." if lang == "en" else "Geen replaybestand opgegeven voor de AI Coach."
        replay_path = prompt_for_replay_path(msg, lang=lang)

    parsed_data, val_path = _load_and_parse_match(replay_path, lang=lang)
    target_player = _select_target_player(parsed_data["players"], player, interactive=True, lang=lang)

    # Gamemode and map position prompts
    meta_dict = parsed_data["metadata"]
    detected_mode = meta_dict.get("gamemode") or ("Team Game" if len(parsed_data["players"]) > 2 else "1v1 Random Map")
    actual_gamemode = gamemode or _prompt_gamemode(detected_mode, interactive=True, lang=lang)

    is_tg = (len(parsed_data["players"]) > 2) or ("team" in actual_gamemode.lower())
    detected_pos = "Flank" if is_tg else "Solo (1v1)"
    actual_position = position or _prompt_map_position(detected_pos, is_team_game=is_tg, interactive=True, lang=lang)

    user_question = prompt
    if not user_question:
        q_msg = (
            "\n💬 [bold yellow]Any specific question or focus area for the coach? (optional, press Enter to skip): [/bold yellow]"
            if lang == "en"
            else "\n💬 [bold yellow]Specifieke vraag of focuspunt voor de coach? (optioneel, druk op Enter om over te slaan): [/bold yellow]"
        )
        q = console.input(q_msg).strip()
        if q:
            user_question = q

    match_obj = parsed_data.get("match")
    raw_inputs = extract_player_inputs(match_obj, target_player["number"]) if match_obj else []

    report = build_telemetry_report(
        parsed_data["metadata"], target_player, parsed_data["players"],
        parsed_data["uptimes"], parsed_data["gaia"], raw_inputs, parsed_data["metadata"]["game_duration_s"],
        gamemode=actual_gamemode, map_position=actual_position,
    )

    stem = val_path.stem
    export_json(report, output_dir, stem)
    export_markdown(report, output_dir, stem)

    status_msg = f"[bold cyan]Consulting AI Coach ({lang.upper()}) via Gemini...[/bold cyan]" if lang == "en" else f"[bold cyan]AI Coach raadplegen ({lang.upper()}) via Gemini...[/bold cyan]"
    console.print(status_msg)

    try:
        raw_coaching = call_coach_llm(
            report_json=truncate_payload_for_llm(report),
            language=lang,
            model=model,
            target_civ=target_player.get("civilization"),
            user_question=user_question,
        )
    except AIAnalysisError as e:
        console.print(f"[bold red]AI Coaching Error:[/bold red] {e}")
        raise typer.Exit(code=1)

    coaching_report = parse_coaching_response(raw_coaching, target_player["name"], stem, language=lang)
    coaching_path = export_coaching(coaching_report, output_dir, stem)

    panel_msg = (
        f"[bold green]Coaching Analysis Successfully Generated![/bold green]\nSaved to: [cyan]{coaching_path}[/cyan]"
        if lang == "en"
        else f"[bold green]Coaching Analyse Succesvol Gegenereerd![/bold green]\nOpgeslagen in: [cyan]{coaching_path}[/cyan]"
    )
    console.print(Panel.fit(panel_msg, title="AoE2 AI Coach"))
    console.print(Markdown(raw_coaching))

    if report.target_player.scores:
        sc = report.target_player.scores
        idle_s = report.target_player.dark_age.total_idle_tc_s
        by_age_str = ", ".join(f"{age.split()[0]}: {cnt}" for age, cnt in sc.military_by_age.items()) if sc.military_by_age else f"{sc.total_military_units}"
        top_lines_str = ", ".join(f"{line} ({cnt})" for line, cnt in list(sc.top_military_lines.items())[:3])
        if lang == "en":
            lines_desc = f"\n  [dim]↳ Top Unit Lines: {top_lines_str}[/dim]" if top_lines_str else ""
            content = (
                f"• [bold]Match Format & Role:[/bold]           [bold magenta]{report.metadata.gamemode}[/bold magenta] ({report.metadata.map_position or 'Standard'})\n"
                f"• [bold]Town Center Uptime (Dark Age):[/bold]  [bold cyan]{sc.tc_uptime_pct}%[/bold cyan] "
                f"([dim]Idle: {sc.tc_idle_pct}% | {format_timestamp(idle_s)} min[/dim])\n"
                f"• [bold]Economy Efficiency Score:[/bold]       [bold cyan]{sc.eco_efficiency_score}%[/bold cyan]\n"
                f"• [bold]Military Value & Focus Score:[/bold]   [bold cyan]{sc.military_value_score}%[/bold cyan] "
                f"([dim]{sc.total_military_units} units total: {by_age_str}[/dim]){lines_desc}"
            )
            title = "📊 Match Performance Benchmarks"
        else:
            lines_desc = f"\n  [dim]↳ Belangrijkste Eenheden: {top_lines_str}[/dim]" if top_lines_str else ""
            content = (
                f"• [bold]Wedstrijd Format & Rol:[/bold]         [bold magenta]{report.metadata.gamemode}[/bold magenta] ({report.metadata.map_position or 'Standaard'})\n"
                f"• [bold]Town Center Uptime (Dark Age):[/bold]  [bold cyan]{sc.tc_uptime_pct}%[/bold cyan] "
                f"([dim]Idle: {sc.tc_idle_pct}% | {format_timestamp(idle_s)} min[/dim])\n"
                f"• [bold]Economie Efficiëntie Score:[/bold]     [bold cyan]{sc.eco_efficiency_score}%[/bold cyan]\n"
                f"• [bold]Militaire Waarde & Focus:[/bold]        [bold cyan]{sc.military_value_score}%[/bold cyan] "
                f"([dim]{sc.total_military_units} eenheden totaal: {by_age_str}[/dim]){lines_desc}"
            )
            title = "📊 Wedstrijd Prestatie Scores"
        console.print(Panel(content, title=title, border_style="cyan"))


def main() -> None:
    """Smart CLI launcher that handles drag-and-drop, direct file args, and interactive runs."""
    if len(sys.argv) == 2 and sys.argv[1] not in ["convert", "coach", "--help", "-h"]:
        sys.argv.insert(1, "coach")
    elif len(sys.argv) == 1:
        sys.argv.append("coach")
    app()


if __name__ == "__main__":
    main()
