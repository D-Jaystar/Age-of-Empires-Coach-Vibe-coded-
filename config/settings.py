"""config/settings.py - Application configuration and AoE2 constants."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Environment configuration settings."""

    @classmethod
    def gemini_api_key(cls) -> str:
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise EnvironmentError("GEMINI_API_KEY is not set. Add it to your .env file.")
        return key

    @classmethod
    def gemini_model(cls) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

    @classmethod
    def output_dir(cls) -> Path:
        return Path(os.getenv("OUTPUT_DIR", "output").strip() or "output")


@dataclass(frozen=True)
class AoE2Constants:
    """AoE2 Definitive Edition timing and benchmark constants (in seconds)."""
    VILLAGER_TRAIN_TIME_S: int = 25
    LOOM_RESEARCH_TIME_S: int = 25
    FEUDAL_AGE_RESEARCH_TIME_S: int = 130
    CASTLE_AGE_RESEARCH_TIME_S: int = 160
    IMPERIAL_AGE_RESEARCH_TIME_S: int = 190
    IDLE_TC_GAP_THRESHOLD_S: int = 30
    DARK_AGE_BENCHMARK_FEUDAL_CLICK_S: tuple[int, int] = (480, 540)
    MIN_GAME_DURATION_S: int = 120


AOE2 = AoE2Constants()

WATER_MAP_KEYWORDS: frozenset[str] = frozenset({
    "islands", "team islands", "migration", "archipelago", "baltic",
    "mediterranean", "rivers", "four lakes", "cross", "scandinavia",
    "bog islands", "wade", "water nomad", "land nomad", "continental",
    "coastal", "pilgrims", "viking islands", "holy island", "paradise island",
})
