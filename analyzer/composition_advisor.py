"""analyzer/composition_advisor.py
=================================

Real-Time & Matchup Tactical Composition and Upgrade Advisor.
Analyzes Player Civ vs Opponent Civ (and detected unit lines) to generate:
- 1-2 Recommended Army Compositions (Plan A & Plan B)
- Tactical rationale (why this combo counters the opponent)
- Critical Upgrade Prioritization & Missing Upgrades Alert
- Civilization Perks & Tech Restriction Guardrails
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from data.civ_database import get_civilization, load_civilizations


class CompositionPlan(BaseModel):
    """Military composition archetype with tactical rationale."""
    name: str
    archetype: str  # e.g., "Heavy Cavalry + Melee Anti-Pike", "Crossbow Mass + Meatshield"
    primary_unit: str
    secondary_unit: str
    siege_support: str
    rationale: str
    food_heavy: bool = False
    wood_heavy: bool = False
    gold_dependent: bool = True


class UpgradeRequirement(BaseModel):
    """An upgrade with its priority, building, and tactical impact."""
    tech_name: str
    building: str  # Blacksmith, University, Monastery, Castle, Barracks, Stable, Archery Range
    age: str  # Feudal, Castle, Imperial
    priority: int  # 1 = Urgent / Core Win-Con, 2 = High, 3 = Situational
    impact: str  # e.g. "+1/+1 Pierce & Melee Armor for Cavalry against TC fire"
    is_researched: bool = False


class MatchupAdvice(BaseModel):
    """Comprehensive real-time tactical advice for a civ matchup."""
    player_civ: str
    opponent_civ: str
    current_age: str
    plan_a: CompositionPlan
    plan_b: CompositionPlan
    missing_critical_upgrade: Optional[str] = None
    missing_upgrade_detail: Optional[str] = None
    upgrades_roadmap: list[UpgradeRequirement] = Field(default_factory=list)
    civ_perks: list[str] = Field(default_factory=list)
    tech_restrictions: str = ""


# Civ archetype lookup for counter generation
CIV_ARCHETYPES = {
    "Cavalry": {"Franks", "Magyars", "Huns", "Lithuanians", "Berbers", "Poles", "Bulgarians", "Burgundians", "Cumans"},
    "Archers": {"Britons", "Ethiopians", "Mayans", "Vietnamese", "Chinese", "Italians", "Dravidians"},
    "Infantry": {"Goths", "Teutons", "Romans", "Celts", "Malians", "Japanese", "Slavs", "Vikings", "Armenians", "Incas", "Aztecs"},
    "Camel/Naval": {"Saracens", "Berbers", "Hindustanis", "Gurjaras", "Byzantines"},
    "Cavalry Archer": {"Mongols", "Tatars", "Turks", "Huns", "Magyars"},
    "Gunpowder/Defensive": {"Turks", "Bohemians", "Byzantines", "Koreans", "Spanish"},
    "Monks/Siege": {"Aztecs", "Slavs", "Bengalis", "Saracens", "Bohemians"},
}


def _detect_civ_archetype(civ_name: str) -> str:
    """Classify civilization into a dominant strategic archetype."""
    clean = civ_name.strip().title()
    for arch, civs in CIV_ARCHETYPES.items():
        if clean in civs:
            return arch
    data = get_civilization(clean)
    if data:
        focus = data.get("focus", "").lower()
        if "cavalry" in focus:
            return "Cavalry"
        if "archer" in focus:
            return "Archers"
        if "infantry" in focus:
            return "Infantry"
        if "camel" in focus:
            return "Camel/Naval"
    return "General"


def generate_matchup_advice(
    player_civ: str,
    opponent_civ: str,
    current_age: str = "Castle Age",
    researched_techs: list[str] | None = None,
    opponent_units: list[str] | None = None,
) -> MatchupAdvice:
    """Generate tactical composition and upgrade intelligence in English.

    Guard Clauses:
        - Normalizes civ names, falls back to sensible defaults on unknown civs.
    """
    p_data = get_civilization(player_civ) or {}
    o_data = get_civilization(opponent_civ) or {}

    p_clean = player_civ.strip().title() if player_civ else "Franks"
    o_clean = opponent_civ.strip().title() if opponent_civ else "Saracens"

    p_archetype = _detect_civ_archetype(p_clean)
    o_archetype = _detect_civ_archetype(o_clean)

    researched_set = {t.lower() for t in (researched_techs or [])}

    # 1. Determine Player's Plan A & Plan B based on matchup
    # Default tailored for Franks / Cavalry
    if "Cavalry" in p_archetype or p_clean == "Franks":
        if o_archetype in ("Camel/Naval", "Infantry") or o_clean in ("Saracens", "Goths", "Hindustanis", "Gurjaras"):
            # Against heavy camel or halberdier threat
            plan_a = CompositionPlan(
                name="Cavalier + Throwing Axeman",
                archetype="Heavy Cavalry + Ranged Melee Counter",
                primary_unit="Knight / Cavalier line",
                secondary_unit="Throwing Axeman (or Hand Cannoneer / Skirmisher)",
                siege_support="Battering Ram / Trebuchet",
                rationale=(
                    f"Against {o_clean}'s anti-cavalry options (Camels/Halberdiers), pure Knights will trade inefficiently. "
                    "Throwing Axemen deal ranged melee damage that shreds Pikes and Camels before they touch your Knights."
                ),
                food_heavy=True,
                gold_dependent=True,
            )
            plan_b = CompositionPlan(
                name="Pikeman + Elite Skirmisher + Monk",
                archetype="Trash Counter & Monk Conversion",
                primary_unit="Pikeman",
                secondary_unit="Elite Skirmisher",
                siege_support="Mangonel / Scorpion",
                rationale=(
                    "Cost-effective defensive counter. Preserves gold while converting high-value enemy cavalry or camels, "
                    "protecting your economy while building up towards a Castle Age deathball."
                ),
                food_heavy=True,
                wood_heavy=True,
                gold_dependent=False,
            )
        else:
            # Against Archer or standard civs
            plan_a = CompositionPlan(
                name="Knights + Crossbow / Skirmisher",
                archetype="Heavy Cavalry Spearhead",
                primary_unit="Knight / Cavalier line",
                secondary_unit="Elite Skirmisher (vs Crossbows) or Crossbowman",
                siege_support="Mangonel / Battering Ram",
                rationale=(
                    f"Your +20% HP cavalry overpowers {o_clean}'s armies. "
                    "Pair Knights with Skirmishers to pick off enemy Spearmen and absorb arrow fire, allowing your Knights to raid freely."
                ),
                food_heavy=True,
                gold_dependent=True,
            )
            plan_b = CompositionPlan(
                name="Light Cavalry + Throwing Axeman",
                archetype="High-Mobility Raid Composition",
                primary_unit="Light Cavalry (Hussar)",
                secondary_unit="Throwing Axeman",
                siege_support="Petards / Rams",
                rationale=(
                    "Mobile raiding composition that consumes zero gold for primary units. "
                    "Light Cavalry soaks arrow damage while Axemen tear down counter-units."
                ),
                food_heavy=True,
                wood_heavy=True,
                gold_dependent=False,
            )

    elif "Archer" in p_archetype or p_clean in ("Britons", "Ethiopians", "Mayans"):
        if o_archetype in ("Cavalry",) or o_clean in ("Franks", "Magyars", "Huns"):
            plan_a = CompositionPlan(
                name="Crossbowman + Pikeman",
                archetype="Ranged Mass + Anti-Cavalry Shield",
                primary_unit="Crossbowman / Arbalester",
                secondary_unit="Pikeman / Halberdier",
                siege_support="Mangonel / Trebuchet",
                rationale=(
                    f"{o_clean} excels at heavy cavalry. A meatshield of Pikemen absorbs cavalry charges, "
                    "allowing your massed Crossbows to focus-fire enemy Knights without taking melee damage."
                ),
                wood_heavy=True,
                gold_dependent=True,
            )
            plan_b = CompositionPlan(
                name="Longbowman / Unique Archer + Light Cav",
                archetype="Long-Range Denial + Map Control",
                primary_unit="Unique Unit (Longbowman / Plumed Archer)",
                secondary_unit="Light Cavalry",
                siege_support="Battering Ram / Trebuchet",
                rationale=(
                    "Outranges enemy Town Centers and defensive buildings. Light Cavalry controls relics and counters enemy Skirmishers."
                ),
                wood_heavy=True,
                gold_dependent=True,
            )
        else:
            plan_a = CompositionPlan(
                name="Arbalester + Siege Ram / Onager",
                archetype="Mass Ranged Siege Push",
                primary_unit="Crossbowman / Arbalester",
                secondary_unit="Knight (Castle Age) or Halberdier",
                siege_support="Siege Ram / Mangonel",
                rationale=(
                    "Devastating push composition. Siege Rams absorb enemy defensive fire while massed archers eliminate enemy units."
                ),
                wood_heavy=True,
                gold_dependent=True,
            )
            plan_b = CompositionPlan(
                name="Elite Skirmisher + Halberdier",
                archetype="Full Trash War",
                primary_unit="Elite Skirmisher",
                secondary_unit="Halberdier",
                siege_support="Scorpion / Ram",
                rationale="Zero-gold counter composition designed to drain opponent resources when gold runs out.",
                wood_heavy=True,
                food_heavy=True,
                gold_dependent=False,
            )

    elif p_clean == "Byzantines":
        plan_a = CompositionPlan(
            name="Cataphract + Cheap Halberdier + Cheap Skirm",
            archetype="Anti-Infantry Elite Cavalry + Trash Wall",
            primary_unit="Cataphract (Castle/Imp)",
            secondary_unit="Pikeman / Halberdier (-25% cost)",
            siege_support="Trebuchet / Bombard Cannon",
            rationale=(
                f"Against {o_clean}, exploit your -25% trash discount to build an unbreakable frontline, "
                "while Cataphracts obliterate enemy infantry and trample support units with Logistica trample damage."
            ),
            food_heavy=True,
            gold_dependent=True,
        )
        plan_b = CompositionPlan(
            name="Cheap Camels (-25%) + Crossbowman",
            archetype="Cavalry Shutdown & Firepower",
            primary_unit="Camel Rider (-25% discount)",
            secondary_unit="Crossbowman",
            siege_support="Mangonel",
            rationale="Cost-effectively shuts down enemy Knight lines with ultra-cheap Camels while archers provide ranged DPS.",
            food_heavy=True,
            gold_dependent=True,
        )

    else:
        # Generic balanced plan
        plan_a = CompositionPlan(
            name="Knight line + Crossbow line",
            archetype="Classic Castle Age Castle Power Spike",
            primary_unit="Knights",
            secondary_unit="Crossbowman",
            siege_support="Mangonel",
            rationale=f"Balanced two-unit gold composition giving high mobility and ranged firepower against {o_clean}.",
            food_heavy=True,
            gold_dependent=True,
        )
        plan_b = CompositionPlan(
            name="Pikeman + Elite Skirmisher",
            archetype="Full Trash Counter",
            primary_unit="Pikeman",
            secondary_unit="Elite Skirmisher",
            siege_support="Battering Ram",
            rationale="Zero-gold counter army saving your gold for tech transitions.",
            food_heavy=True,
            wood_heavy=True,
            gold_dependent=False,
        )

    # 2. Build Upgrades Roadmap based on chosen composition
    upgrades: list[UpgradeRequirement] = []

    is_cavalry_plan = (
        "Knight" in plan_a.primary_unit
        or "Cavalier" in plan_a.primary_unit
        or "Cavalier" in plan_a.name
        or plan_a.archetype.startswith("Heavy Cavalry")
    )
    is_archer_plan = (
        "Crossbow" in plan_a.primary_unit
        or "Arbalester" in plan_a.primary_unit
        or "Crossbow" in plan_a.name
        or "Arbalester" in plan_a.name
        or "Ranged Mass" in plan_a.archetype
        or "Archer" in plan_a.archetype
    )

    if is_cavalry_plan:
        upgrades.extend([
            UpgradeRequirement(
                tech_name="Chain Barding Armor",
                building="Blacksmith",
                age="Castle",
                priority=1,
                impact="+1/+1 Armor (+2/+2 total). ESSENTIAL: Knights survive TC fire and cross arrows",
                is_researched="chain barding armor" in researched_set,
            ),
            UpgradeRequirement(
                tech_name="Iron Casting",
                building="Blacksmith",
                age="Castle",
                priority=2,
                impact="+1 Melee attack (+2 total), kills villagers and archers in 1 fewer hit",
                is_researched="iron casting" in researched_set,
            ),
            UpgradeRequirement(
                tech_name="Husbandry",
                building="Stable",
                age="Castle",
                priority=2,
                impact="+10% cavalry speed, essential for chasing down Crossbows or retreating safely",
                is_researched="husbandry" in researched_set,
            ),
            UpgradeRequirement(
                tech_name="Plate Barding Armor",
                building="Blacksmith",
                age="Imperial",
                priority=1,
                impact="+1/+2 Armor (+3/+4 total). Turns Cavaliers/Paladins into unstoppable juggernauts",
                is_researched="plate barding armor" in researched_set,
            ),
        ])
        if p_clean != "Franks":  # Franks get +20% HP and don't have bloodlines
            upgrades.insert(0, UpgradeRequirement(
                tech_name="Bloodlines",
                building="Stable",
                age="Feudal",
                priority=1,
                impact="+20 HP to all cavalry. Mandatory foundation for all cavalry fights",
                is_researched="bloodlines" in researched_set,
            ))

    elif is_archer_plan:
        upgrades.extend([
            UpgradeRequirement(
                tech_name="Bodkin Arrow",
                building="Blacksmith",
                age="Castle",
                priority=1,
                impact="+1 Range and +1 Attack. Priority #1 upon reaching Castle Age",
                is_researched="bodkin arrow" in researched_set,
            ),
            UpgradeRequirement(
                tech_name="Ballistics",
                building="University",
                age="Castle",
                priority=1,
                impact="Arrows track moving targets. Without this, Crossbows miss 60%+ of their shots against moving units",
                is_researched="ballistics" in researched_set,
            ),
            UpgradeRequirement(
                tech_name="Leather Archer Armor",
                building="Blacksmith",
                age="Castle",
                priority=2,
                impact="+1/+1 Armor. Crucial in Crossbow vs Crossbow and Crossbow vs Skirmisher wars",
                is_researched="leather archer armor" in researched_set,
            ),
            UpgradeRequirement(
                tech_name="Thumb Ring",
                building="Archery Range",
                age="Castle",
                priority=2,
                impact="100% accuracy and +18% firing rate for Crossbows",
                is_researched="thumb ring" in researched_set,
            ),
            UpgradeRequirement(
                tech_name="Bracer",
                building="Blacksmith",
                age="Imperial",
                priority=1,
                impact="+1 Range and +1 Attack in Imperial Age",
                is_researched="bracer" in researched_set,
            ),
        ])

    # 3. Find Missing Critical Upgrade
    missing_crit: Optional[str] = None
    missing_detail: Optional[str] = None
    target_age = current_age.replace(" Age", "").strip()

    for u in upgrades:
        if not u.is_researched:
            if u.age == target_age or (target_age == "Castle" and u.age == "Feudal"):
                missing_crit = u.tech_name
                missing_detail = f"Missing {u.tech_name} ({u.building}) - {u.impact}"
                break

    # 4. Civ Perks & Tech Restrictions
    civ_perks = p_data.get("bonuses", [])
    restrictions = p_data.get("tech_restrictions", "Standard tech tree.")

    return MatchupAdvice(
        player_civ=p_clean,
        opponent_civ=o_clean,
        current_age=current_age,
        plan_a=plan_a,
        plan_b=plan_b,
        missing_critical_upgrade=missing_crit,
        missing_upgrade_detail=missing_detail,
        upgrades_roadmap=upgrades,
        civ_perks=civ_perks,
        tech_restrictions=restrictions,
    )
