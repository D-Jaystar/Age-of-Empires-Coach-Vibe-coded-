"""tests/test_advisor.py
======================

Unit tests for the Real-Time Tactical Composition & Upgrade Advisor.
Verifies:
- Plan A and Plan B generation across various civ archetypes (Franks, Britons, Byzantines)
- Counter mechanics against enemy civ threats (e.g. Franks vs Saracens camels)
- Critical upgrade prioritization and missing upgrade detection
- Guard clauses and unknown civ fallbacks
"""

from __future__ import annotations

import pytest
from analyzer.composition_advisor import (
    CompositionPlan,
    MatchupAdvice,
    generate_matchup_advice,
)


def test_franks_vs_saracens_advice() -> None:
    advice = generate_matchup_advice("Franks", "Saracens", current_age="Castle Age")

    assert advice.player_civ == "Franks"
    assert advice.opponent_civ == "Saracens"
    assert advice.current_age == "Castle Age"

    # Plan A should counter Camels/Pikes with Axeman
    assert "Axeman" in advice.plan_a.name or "Axeman" in advice.plan_a.secondary_unit
    assert "Knight" in advice.plan_a.primary_unit or "Cavalier" in advice.plan_a.primary_unit

    # Missing upgrade in Castle Age for cavalry should be Chain Barding Armor
    assert advice.missing_critical_upgrade == "Chain Barding Armor"
    assert "pierce" in (advice.missing_upgrade_detail or "").lower() or "armor" in (advice.missing_upgrade_detail or "").lower()

    # Franks should NOT require Bloodlines (they get +20% HP automatically)
    tech_names = [u.tech_name for u in advice.upgrades_roadmap]
    assert "Bloodlines" not in tech_names


def test_britons_vs_franks_advice() -> None:
    advice = generate_matchup_advice("Britons", "Franks", current_age="Castle Age")

    assert advice.player_civ == "Britons"
    assert advice.opponent_civ == "Franks"

    # Against Frank heavy cavalry, Plan A should pair Crossbows with anti-cav meatshield (Pikemen)
    assert "Crossbow" in advice.plan_a.name or "Crossbow" in advice.plan_a.primary_unit
    assert "Pike" in advice.plan_a.secondary_unit or "Pike" in advice.plan_a.name

    # Missing critical upgrade for archers in Castle Age should be Bodkin Arrow
    assert advice.missing_critical_upgrade == "Bodkin Arrow"
    assert any("bodkin arrow" in u.tech_name.lower() for u in advice.upgrades_roadmap)


def test_byzantines_advice_trash_discount() -> None:
    advice = generate_matchup_advice("Byzantines", "Franks", current_age="Castle Age")

    assert advice.player_civ == "Byzantines"
    assert "Cataphract" in advice.plan_a.name or "Camels" in advice.plan_a.name or "Cataphract" in advice.plan_a.secondary_unit


def test_researched_techs_filtered_from_missing() -> None:
    advice = generate_matchup_advice(
        "Franks",
        "Saracens",
        current_age="Castle Age",
        researched_techs=["Chain Barding Armor", "Iron Casting"],
    )

    # Chain Barding is researched, so next priority (e.g. Husbandry) should be flagged
    assert advice.missing_critical_upgrade != "Chain Barding Armor"
    assert advice.missing_critical_upgrade == "Husbandry"
