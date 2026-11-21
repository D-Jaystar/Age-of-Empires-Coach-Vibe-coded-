"""analyzer/military_heuristics.py
==============================

Calculates military strategy, unit composition, and upgrade timing heuristics:
- Opening strategy detection (Scouts, Archers, Men-at-Arms, Fast Castle, Boom)
- Early Gold inefficiency flag (e.g. taking gold during a pure Scouts opening)
- Castle Age military composition focus score vs scattered production
- Military building construction counts
- Blacksmith, Stable, Range, and Barracks upgrade timelines
- Production building scaling during age transitions
"""

from __future__ import annotations

from typing import Any

from data.models import BuildOrderEntry


# Canonical unit line classifications
UNIT_LINE_MAP: dict[str, str] = {
    # Cavalry
    "scout cavalry": "Scout / Light Cavalry",
    "light cavalry": "Scout / Light Cavalry",
    "hussar": "Scout / Light Cavalry",
    "knight": "Knight line",
    "cavalier": "Knight line",
    "paladin": "Knight line",
    "camel rider": "Camel line",
    "heavy camel rider": "Camel line",
    "imperial camel rider": "Camel line",
    "steppe lancer": "Steppe Lancer",
    "elite steppe lancer": "Steppe Lancer",
    "battle elephant": "Battle Elephant",
    "elite battle elephant": "Battle Elephant",
    # Archers
    "archer": "Archer / Crossbow line",
    "crossbowman": "Archer / Crossbow line",
    "arbalester": "Archer / Crossbow line",
    "skirmisher": "Skirmisher line",
    "elite skirmisher": "Skirmisher line",
    "imperial skirmisher": "Skirmisher line",
    "cavalry archer": "Cavalry Archer",
    "heavy cavalry archer": "Cavalry Archer",
    "genitour": "Genitour",
    "slinger": "Slinger",
    # Infantry
    "militia": "Militia line",
    "man-at-arms": "Militia line",
    "long swordsman": "Militia line",
    "two-handed swordsman": "Militia line",
    "champion": "Militia line",
    "spearman": "Spearman line",
    "pikeman": "Spearman line",
    "halberdier": "Spearman line",
    "eagle scout": "Eagle line",
    "eagle warrior": "Eagle line",
    "elite eagle warrior": "Eagle line",
    "condottiero": "Condottiero",
    # Gunpowder
    "hand cannoneer": "Hand Cannoneer",
    "bombard cannon": "Bombard Cannon",
    "petard": "Petard",
    # Siege
    "battering ram": "Ram line",
    "capped ram": "Ram line",
    "siege ram": "Ram line",
    "mangonel": "Mangonel line",
    "onager": "Mangonel line",
    "siege onager": "Mangonel line",
    "scorpion": "Scorpion line",
    "heavy scorpion": "Scorpion line",
    "armored elephant": "Siege Elephant line",
    "siege elephant": "Siege Elephant line",
    "trebuchet": "Trebuchet",
    # Monk
    "monk": "Monk",
    "missionary": "Missionary",
    # Navy / Warships
    "galley": "Galley line",
    "war galley": "Galley line",
    "galleon": "Galley line",
    "fire galley": "Fire ship line",
    "fire ship": "Fire ship line",
    "fast fire ship": "Fire ship line",
    "demolition raft": "Demolition ship line",
    "demolition ship": "Demolition ship line",
    "heavy demolition ship": "Demolition ship line",
    "cannon galleon": "Cannon Galleon",
    "elite cannon galleon": "Cannon Galleon",
    "dromon": "Dromon",
    "caravel": "Caravel",
    "longboat": "Longboat",
    "turtle ship": "Turtle Ship",
    # Unique Units
    "konnik": "Konnik",
    "longbowman": "Longbowman",
    "cataphract": "Cataphract",
    "chu ko nu": "Chu Ko Nu",
    "huskarl": "Huskarl",
    "samurai": "Samurai",
    "mangudai": "Mangudai",
    "war elephant": "War Elephant",
    "mameluke": "Mameluke",
    "teutonic knight": "Teutonic Knight",
    "woad raider": "Woad Raider",
    "janissary": "Janissary",
    "berserk": "Berserk",
    "plumed archer": "Plumed Archer",
    "conquistador": "Conquistador",
    "tarkan": "Tarkan",
    "war wagon": "War Wagon",
    "jaguar warrior": "Jaguar Warrior",
    "kamayuk": "Kamayuk",
    "boyar": "Boyar",
    "magyar huszar": "Magyar Huszar",
    "genoese crossbowman": "Genoese Crossbowman",
    "camel archer": "Camel Archer",
    "shotel warrior": "Shotel Warrior",
    "gbeto": "Gbeto",
    "arambai": "Arambai",
    "ballista elephant": "Ballista Elephant",
    "karambit warrior": "Karambit Warrior",
    "rattan archer": "Rattan Archer",
    "keshik": "Keshik",
    "leitis": "Leitis",
    "kipchak": "Kipchak",
    "coustillier": "Coustillier",
    "serjeant": "Serjeant",
    "obuch": "Obuch",
    "hussite wagon": "Hussite Wagon",
    "urumi swordsman": "Urumi Swordsman",
    "chakram thrower": "Chakram Thrower",
    "ghulam": "Ghulam",
    "shrivamsha rider": "Shrivamsha Rider",
    "centurion": "Centurion",
    "legionary": "Legionary",
    "composite bowman": "Composite Bowman",
    "monaspa": "Monaspa",
}

NON_MILITARY_UNITS: frozenset[str] = frozenset({
    "villager", "trade cart", "fishing ship", "transport ship", "relic", "sheep", "cow", "boar"
})

BLACKSMITH_TECHS: frozenset[str] = frozenset({
    "forging", "iron casting", "blast furnace",
    "scale barding armor", "chain barding armor", "plate barding armor",
    "scale mail armor", "chain mail armor", "plate mail armor",
    "padded archer armor", "leather archer armor", "ring archer armor",
    "fletching", "bodkin arrow", "bracer",
    "bloodlines", "husbandry", "thumb ring", "parthian tactics",
    "ballistics", "chemistry", "squires", "supplies", "arson",
})


def detect_opening_strategy(
    feudal_events: list[dict[str, Any]] | None,
    dark_events: list[dict[str, Any]] | None,
) -> str:
    """Detect the player's opening strategy based on early buildings and military units.

    Classifications:
        - 'scouts': Early Stable + Scout Cavalry production.
        - 'archers': Early Archery Range + Archer/Skirmisher production.
        - 'maa': Dark Age Barracks + Militia before Feudal completion.
        - 'fast_castle': Minimal military buildings; rapid transition (Market + Blacksmith).
        - 'boom': Multiple Town Centers added quickly without military investment.
        - 'unknown': Insufficient or unclassifiable actions.

    Guard Clauses:
        - If both feudal_events and dark_events are empty, returns 'unknown'.
    """
    if not feudal_events and not dark_events:
        return "unknown"

    all_events = (dark_events or []) + (feudal_events or [])
    all_events.sort(key=lambda x: float(x.get("timestamp_s", 0.0)))

    stable_count = 0
    range_count = 0
    barracks_count = 0
    militia_count = 0
    scout_count = 0
    archer_count = 0
    has_market = False
    has_blacksmith = False

    for ev in all_events:
        t = float(ev.get("timestamp_s", 0.0))
        # Look only at early game (first 16 minutes / 960s)
        if t > 960.0:
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "stable" in param and "build" in inp_type:
            stable_count += 1
        elif "archery range" in param and "build" in inp_type:
            range_count += 1
        elif "barracks" in param and "build" in inp_type:
            barracks_count += 1
        elif "market" in param and "build" in inp_type:
            has_market = True
        elif "blacksmith" in param and "build" in inp_type:
            has_blacksmith = True
        elif "militia" in param or "man-at-arms" in param:
            militia_count += 1
        elif "scout cavalry" in param:
            scout_count += 1
        elif "archer" in param or "skirmisher" in param:
            archer_count += 1

    # Strategy evaluation priority:
    # 1. Men-at-Arms opening
    if militia_count >= 2 and (range_count > 0 or barracks_count > 0):
        return "maa"

    # 2. Scouts opening
    if stable_count > 0 and (scout_count > 0 or stable_count >= range_count):
        return "scouts"

    # 3. Archers opening
    if range_count > 0 and (archer_count > 0 or range_count > stable_count):
        return "archers"

    # 4. Fast Castle
    if has_market and has_blacksmith and stable_count == 0 and range_count == 0:
        return "fast_castle"

    if stable_count > 0:
        return "scouts"
    if range_count > 0:
        return "archers"

    return "unknown"


def detect_early_gold(
    events: list[dict[str, Any]] | None,
    opening: str,
    age_start_s: float,
    age_end_s: float,
) -> bool:
    """Flag if player mined gold or built a Mining Camp too early during a Scouts opening.

    In a pure Scouts opening, gold is not required until preparing for Castle Age
    or Bloodlines. Gathering gold early in Dark/early Feudal delays food/farms.

    Guard Clauses:
        - If events is None or empty, returns False.
        - If opening is not 'scouts', early gold is expected (e.g. Archers, M@A).
    """
    if not events or opening != "scouts":
        return False

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < age_start_s:
            continue
        # Check first 4 minutes of Feudal Age
        if t > (age_start_s + 240.0):
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "mining camp" in param and "build" in inp_type:
            # Check if this mining camp was placed early
            return True
        if "gold" in param and "gather" in inp_type:
            return True

    return False


def extract_military_units(
    events: list[dict[str, Any]] | None,
    start_s: float,
    end_s: float,
) -> tuple[int, dict[str, int]]:
    """Count military units queued and breakdown by unit line in a time window.

    Guard Clauses:
        - If events is None or empty, returns (0, {}).
    """
    if not events:
        return 0, {}

    line_counts: dict[str, int] = {}
    total = 0

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < start_s:
            continue
        if t > end_s:
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "queue" in inp_type or "train" in inp_type:
            if any(nm in param for nm in NON_MILITARY_UNITS) or not param.strip():
                continue

            matched = False
            for unit_key, canonical_line in UNIT_LINE_MAP.items():
                if unit_key in param:
                    line_counts[canonical_line] = line_counts.get(canonical_line, 0) + 1
                    total += 1
                    matched = True
                    break

            if not matched and param and param != "none":
                unit_label = f"Unit ({param.title()})"
                line_counts[unit_label] = line_counts.get(unit_label, 0) + 1
                total += 1

    return total, line_counts


def calculate_composition_focus(
    events: list[dict[str, Any]] | None,
    start_s: float,
    end_s: float,
) -> tuple[float, list[str], dict[str, int], bool]:
    """Calculate military composition focus score and flag scattered army production.

    Commitment to 1 or 2 complementary unit lines (e.g. Knights + Skirmishers) represents
    high focus (0.85 - 1.0). Spreading resources across 3+ unrelated unit lines
    delays upgrades and diminishes power-spikes (scattered flag = True).

    Guard Clauses:
        - If events is None or empty, returns (1.0, [], {}, False).

    Returns:
        tuple[focus_score, distinct_lines, line_counts, is_scattered_flag].
    """
    if not events:
        return 1.0, [], {}, False

    _, line_counts = extract_military_units(events, start_s, end_s)
    distinct_lines = sorted(line_counts.keys())
    num_lines = len(distinct_lines)

    if num_lines == 0:
        return 1.0, [], {}, False
    if num_lines == 1:
        return 1.0, distinct_lines, line_counts, False
    if num_lines == 2:
        return 0.85, distinct_lines, line_counts, False
    if num_lines == 3:
        # 3 lines: check if third line has very few units (e.g. incidental monks or siege)
        counts = sorted(line_counts.values())
        if counts[0] <= 2:
            return 0.70, distinct_lines, line_counts, False
        return 0.50, distinct_lines, line_counts, True

    # 4 or more distinct unit lines in Castle Age is definitively scattered
    return 0.25, distinct_lines, line_counts, True


def count_military_buildings(
    events: list[dict[str, Any]] | None,
    start_s: float,
    end_s: float,
) -> dict[str, int]:
    """Count military buildings constructed within a specific time window.

    Guard Clauses:
        - If events is None or empty, returns empty dictionary.
    """
    if not events:
        return {}

    counts: dict[str, int] = {}
    military_names = {
        "barracks", "archery range", "stable",
        "siege workshop", "castle", "dock", "monastery",
    }

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < start_s:
            continue
        if t > end_s:
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "build" in inp_type:
            for b_name in military_names:
                if b_name in param:
                    display_name = b_name.title()
                    counts[display_name] = counts.get(display_name, 0) + 1
                    break

    return counts


def extract_blacksmith_upgrades(
    events: list[dict[str, Any]] | None,
    start_s: float,
    end_s: float,
) -> list[BuildOrderEntry]:
    """Extract military and Blacksmith upgrades researched within a time window.

    Guard Clauses:
        - If events is None or empty, returns empty list.
    """
    if not events:
        return []

    upgrades: list[BuildOrderEntry] = []

    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < start_s:
            continue
        if t > end_s:
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "research" in inp_type:
            for tech in BLACKSMITH_TECHS:
                if tech in param:
                    upgrades.append(
                        BuildOrderEntry(
                            timestamp_s=round(t, 1),
                            action_type="research",
                            param=str(ev.get("param")),
                            position_x=ev.get("position_x"),
                            position_y=ev.get("position_y"),
                        )
                    )
                    break

    upgrades.sort(key=lambda x: x.timestamp_s)
    return upgrades


def count_production_scaling(
    events: list[dict[str, Any]] | None,
    transition_start_s: float,
    early_age_end_s: float,
) -> dict[str, int]:
    """Count additional production buildings and Town Centers added during age transition.

    E.g. adding 2 Stables + Town Center during Castle Age transition.

    Guard Clauses:
        - If events is None or empty, returns empty dictionary.
    """
    if not events:
        return {}

    production_names = {
        "stable", "archery range", "barracks",
        "siege workshop", "town center", "castle",
    }

    counts: dict[str, int] = {}
    for ev in events:
        t = float(ev.get("timestamp_s", 0.0))
        if t < transition_start_s:
            continue
        if t > early_age_end_s:
            break

        param = str(ev.get("param", "")).lower()
        inp_type = str(ev.get("type", "")).lower()

        if "build" in inp_type:
            for p_name in production_names:
                if p_name in param:
                    display_name = p_name.title()
                    counts[display_name] = counts.get(display_name, 0) + 1
                    break

    return counts
