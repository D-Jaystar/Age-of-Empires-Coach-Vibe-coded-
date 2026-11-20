"""data/civ_database.py
=====================

Provides access to comprehensive AoE2:DE civilization telemetry:
- Loads data/civilizations.json
- Case-insensitive civ lookup with alias handling
- Formats structured civ profiles for prompt injection
- Generates match-up dynamics between target player and all opponents
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

_CIV_DATABASE: dict[str, dict[str, Any]] | None = None
_CIV_FILE_PATH = Path(__file__).parent / "civilizations.json"


def load_civilizations() -> dict[str, dict[str, Any]]:
    """Load the complete civilization database from JSON.

    Guard Clauses:
        - Caches loaded data in memory for subsequent calls.
        - Raises FileNotFoundError if civilizations.json is missing.
    """
    global _CIV_DATABASE
    if _CIV_DATABASE is not None:
        return _CIV_DATABASE

    if not _CIV_FILE_PATH.exists():
        raise FileNotFoundError(f"Civilizations database not found at {_CIV_FILE_PATH}")

    with open(_CIV_FILE_PATH, "r", encoding="utf-8") as f:
        _CIV_DATABASE = json.load(f)

    return _CIV_DATABASE


def get_civilization(civ_name: str | None) -> dict[str, Any] | None:
    """Retrieve detailed civilization profile by name (case-insensitive).

    Guard Clauses:
        - If civ_name is None or empty, returns None.
    """
    if not civ_name or not civ_name.strip():
        return None

    db = load_civilizations()
    clean_query = civ_name.strip().lower()

    # Exact match (case-insensitive)
    for name, data in db.items():
        if name.lower() == clean_query:
            return data

    # Partial / substring match
    for name, data in db.items():
        if clean_query in name.lower() or name.lower() in clean_query:
            return data

    return None


def format_civ_summary(civ_name: str | None) -> str:
    """Format a compact, high-value civilization summary for prompt injection."""
    if not civ_name:
        return "Unknown Civilization"

    civ_data = get_civilization(civ_name)
    if not civ_data:
        return f"- **{civ_name}**: Standard AoE2 tech tree."

    bonuses_str = "; ".join(civ_data.get("bonuses", []))
    uu_str = ", ".join(civ_data.get("unique_units", []))
    restrictions = civ_data.get("tech_restrictions", "Standard")
    unique_techs = civ_data.get("unique_techs", {})
    ut_str = f"Castle: {unique_techs.get('castle', 'N/A')} | Imp: {unique_techs.get('imperial', 'N/A')}"

    return (
        f"### {civ_name.upper()} ({civ_data.get('focus', 'General')}):\n"
        f"- **Bonuses:** {bonuses_str}\n"
        f"- **Unique Units:** {uu_str}\n"
        f"- **Unique Techs:** {ut_str}\n"
        f"- **CRITICAL TECH RESTRICTIONS:** {restrictions}\n"
    )


def format_matchup_overview(
    target_player_name: str,
    target_player_civ: str,
    opponents: list[dict[str, str]],
) -> str:
    """Generate the strategic match-up context between the coached player and opponents.

    Args:
        target_player_name: In-game name of the coached player.
        target_player_civ: Civ name of the coached player.
        opponents: List of dicts with {'name': str, 'civilization': str}.

    Returns:
        str: Formatted Markdown matchup context for the LLM.
    """
    target_summary = format_civ_summary(target_player_civ)

    opp_lines: list[str] = []
    for i, opp in enumerate(opponents, start=1):
        o_name = opp.get("name", f"Opponent {i}")
        o_civ = opp.get("civilization", "Unknown")
        o_data = get_civilization(o_civ)

        if o_data:
            o_focus = o_data.get("focus", "Versatile")
            o_bonuses = "; ".join(o_data.get("bonuses", [])[:2])
            o_uu = ", ".join(o_data.get("unique_units", []))
            o_restr = o_data.get("tech_restrictions", "")
            opp_lines.append(
                f"- **{o_name}** playing **{o_civ}** ({o_focus}):\n"
                f"  * Key Bonuses: {o_bonuses}\n"
                f"  * Key Units: {o_uu}\n"
                f"  * Key Missing Techs: {o_restr}"
            )
        else:
            opp_lines.append(f"- **{o_name}** playing **{o_civ}**")

    matchup_header = f"### MATCHUP OVERVIEW & CIV COMPOSITIONS:\n"
    matchup_header += f"The analyzed player **{target_player_name}** is playing **{target_player_civ}**.\n\n"
    matchup_header += f"#### Opponent Roster:\n" + "\n".join(opp_lines) + "\n\n"
    matchup_header += f"#### Target Player Civ Details:\n{target_summary}\n"

    return matchup_header
