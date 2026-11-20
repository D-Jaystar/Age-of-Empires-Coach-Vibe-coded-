"""
config/settings.py
===================

Central configuration module for the AgeOfEmpires-Coach application.

Responsibilities:
    - Load environment variables via ``python-dotenv`` at module import time.
    - Expose a ``Settings`` class with classmethods for retrieving env-based
      configuration values (API keys, model selection, output directory).
    - Publish AoE2: Definitive Edition game-mechanic constants through the
      frozen ``AoE2Constants`` dataclass and several module-level lookup
      dictionaries (technology IDs, building IDs, unit class IDs, water-map
      keywords).

Usage::

    from config.settings import Settings, AoE2Constants

    api_key   = Settings.gemini_api_key()
    model     = Settings.gemini_model()
    out_dir   = Settings.output_dir()

    feudal_research = AoE2Constants.FEUDAL_AGE_RESEARCH_TIME_S
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Tuple

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Environment bootstrap – executed once at import time
# ---------------------------------------------------------------------------
load_dotenv()


# ---------------------------------------------------------------------------
# Settings – thin wrapper around environment variables
# ---------------------------------------------------------------------------
class Settings:
    """Classmethods that return environment-driven configuration values.

    Every accessor uses a guard clause: if a *required* variable is missing
    the method raises ``EnvironmentError`` immediately.  Optional variables
    fall back to sensible defaults.
    """

    # -- required -----------------------------------------------------------

    @classmethod
    def gemini_api_key(cls) -> str:
        """Return the Gemini API key.

        Raises:
            EnvironmentError: If ``GEMINI_API_KEY`` is not set or blank.
        """
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise EnvironmentError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file or export it as an environment variable."
            )
        return key

    # -- optional (with defaults) -------------------------------------------

    @classmethod
    def gemini_model(cls) -> str:
        """Return the Gemini model identifier.

        Defaults to ``gemini-3.5-flash`` when ``GEMINI_MODEL`` is unset.
        """
        return os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

    @classmethod
    def output_dir(cls) -> Path:
        """Return the output directory as a :class:`~pathlib.Path`.

        Defaults to ``output`` relative to the current working directory when
        ``OUTPUT_DIR`` is unset.  The directory is **not** created
        automatically; call ``Path.mkdir(parents=True, exist_ok=True)`` when
        you need it on disk.
        """
        raw = os.getenv("OUTPUT_DIR", "output").strip()
        if not raw:
            raw = "output"
        return Path(raw)


# ---------------------------------------------------------------------------
# AoE2: DE timing / benchmark constants (frozen – immutable at runtime)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AoE2Constants:
    """Immutable Age of Empires II: Definitive Edition game-mechanic constants.

    All time values are in **in-game seconds** at normal (1×) speed.

    Attributes:
        VILLAGER_TRAIN_TIME_S:
            Time to train one villager from the Town Center.
        LOOM_RESEARCH_TIME_S:
            Time to research Loom at the Town Center.
        FEUDAL_AGE_RESEARCH_TIME_S:
            Time to advance to the Feudal Age.
        CASTLE_AGE_RESEARCH_TIME_S:
            Time to advance to the Castle Age.
        IMPERIAL_AGE_RESEARCH_TIME_S:
            Time to advance to the Imperial Age.
        IDLE_TC_GAP_THRESHOLD_S:
            Consecutive idle-TC seconds before the gap is flagged.  This is
            the only "soft" constant – adjust it in analysis pipelines as
            needed.
        DARK_AGE_BENCHMARK_FEUDAL_CLICK_S:
            ``(low, high)`` target window for clicking Feudal Age in a
            standard 20–22 pop scouts / archers build order.
        MIN_GAME_DURATION_S:
            Guard against extremely short / aborted games that would skew
            statistics.
    """

    # -- Training & research durations --------------------------------------
    VILLAGER_TRAIN_TIME_S: int = 25
    LOOM_RESEARCH_TIME_S: int = 25
    FEUDAL_AGE_RESEARCH_TIME_S: int = 130
    CASTLE_AGE_RESEARCH_TIME_S: int = 160
    IMPERIAL_AGE_RESEARCH_TIME_S: int = 190

    # -- Analysis thresholds ------------------------------------------------
    IDLE_TC_GAP_THRESHOLD_S: int = 30
    DARK_AGE_BENCHMARK_FEUDAL_CLICK_S: Tuple[int, int] = (480, 540)
    MIN_GAME_DURATION_S: int = 120


# Module-level singleton so callers can reference e.g.
#   ``AoE2Constants.FEUDAL_AGE_RESEARCH_TIME_S`` without instantiation,
# while still benefiting from the frozen-dataclass immutability guarantee.
AOE2 = AoE2Constants()


# ---------------------------------------------------------------------------
# Technology IDs  (from the AoE2:DE data files)
# ---------------------------------------------------------------------------
TECHNOLOGY_IDS: Dict[str, int] = {
    "Loom": 22,
    "Feudal Age": 101,
    "Castle Age": 102,
    "Imperial Age": 103,
    "Wheelbarrow": 213,
    "Hand Cart": 249,
    "Town Watch": 8,
    "Town Patrol": 280,
    "Double-Bit Axe": 202,
    "Bow Saw": 203,
    "Two-Man Saw": 221,
    "Horse Collar": 14,
    "Heavy Plow": 13,
    "Crop Rotation": 12,
    "Gold Mining": 55,
    "Gold Shaft Mining": 182,
    "Stone Mining": 278,
    "Stone Shaft Mining": 279,
    "Ballistics": 93,
    "Chemistry": 47,
    "Lancing": 1514,
}

TECHNOLOGY_NAMES: Dict[int, str] = {v: k for k, v in TECHNOLOGY_IDS.items()}
"""Reverse lookup: technology numeric ID → human-readable name."""


# ---------------------------------------------------------------------------
# Building IDs / names
# ---------------------------------------------------------------------------
BUILDING_IDS: Dict[str, int] = {
    "Town Center": 109,
    "House": 70,
    "Mill": 68,
    "Lumber Camp": 562,
    "Mining Camp": 584,
    "Barracks": 12,
    "Archery Range": 87,
    "Stable": 101,
    "Blacksmith": 103,
    "Market": 84,
    "Monastery": 104,
    "Siege Workshop": 49,
    "Castle": 82,
    "Dock": 45,
    "Farm": 50,
    "Fish Trap": 199,
    "Outpost": 598,
    "Palisade Wall": 72,
    "Stone Wall": 117,
    "Gate": 487,
    "Watch Tower": 79,
    "Guard Tower": 234,
    "Keep": 235,
    "Bombard Tower": 236,
    "University": 209,
}

BUILDING_NAMES: Dict[int, str] = {v: k for k, v in BUILDING_IDS.items()}
"""Reverse lookup: building numeric ID → human-readable name."""


# ---------------------------------------------------------------------------
# Unit class IDs  (used for filtering action-log entries)
# ---------------------------------------------------------------------------
UNIT_CLASS_IDS: Dict[str, int] = {
    "Villager": 4,
    "Infantry": 6,
    "Archer": 0,
    "Cavalry": 12,
    "Siege": 13,
    "Monk": 18,
    "Trade Cart": 19,
    "Fishing Ship": 3,
    "War Ship": 22,
    "Transport Ship": 20,
    "Mounted Archer": 36,
    "King": 59,
}

UNIT_CLASS_NAMES: Dict[int, str] = {v: k for k, v in UNIT_CLASS_IDS.items()}
"""Reverse lookup: unit class numeric ID → human-readable name."""


# ---------------------------------------------------------------------------
# Water / hybrid map detection keywords
# ---------------------------------------------------------------------------
WATER_MAP_KEYWORDS: FrozenSet[str] = frozenset(
    {
        "islands",
        "team islands",
        "migration",
        "archipelago",
        "baltic",
        "mediterranean",
        "rivers",
        "four lakes",
        "cross",
        "scandinavia",
        "bog islands",
        "wade",
        "water nomad",
        "land nomad",          # sometimes mixed water spawns
        "continental",
        "coastal",
        "pilgrims",
        "viking islands",
        "holy island",
        "paradise island",
    }
)
"""Lowercase map-name fragments that indicate a water or hybrid map.

Usage::

    map_lower = parsed_map_name.lower()
    is_water = any(kw in map_lower for kw in WATER_MAP_KEYWORDS)
"""
