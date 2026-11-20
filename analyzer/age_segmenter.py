"""analyzer/age_segmenter.py
==========================

Chronologically segments match events and timelines into AoE2 Ages:
- Dark Age
- Feudal Age
- Castle Age
- Imperial Age

Based on exact research completion timestamps from player uptimes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgeSegment:
    """Represents a continuous time window corresponding to an in-game Age."""

    age_name: str
    start_s: float
    end_s: float | None


def segment_by_age(
    uptimes: dict[str, float] | None,
    game_duration_s: float,
) -> list[AgeSegment]:
    """Segment the match duration into Dark, Feudal, Castle, and Imperial periods.

    Guard Clauses:
        - If game_duration_s <= 0, returns a single Dark Age segment [0, 0].
        - If uptimes is None or empty, returns a single Dark Age segment spanning the whole game.

    Args:
        uptimes: Mapping of age keys ('feudal', 'castle', 'imperial') to timestamps in seconds.
        game_duration_s: Total match duration in seconds.

    Returns:
        list[AgeSegment]: Chronological list of non-overlapping age segments.
    """
    duration = max(0.0, float(game_duration_s))
    if duration == 0.0:
        return [AgeSegment(age_name="Dark Age", start_s=0.0, end_s=0.0)]

    if not uptimes:
        return [AgeSegment(age_name="Dark Age", start_s=0.0, end_s=duration)]

    feudal_s = uptimes.get("feudal")
    castle_s = uptimes.get("castle")
    imperial_s = uptimes.get("imperial")

    segments: list[AgeSegment] = []

    # 1. Dark Age
    if feudal_s is None or feudal_s > duration:
        segments.append(AgeSegment(age_name="Dark Age", start_s=0.0, end_s=duration))
        return segments

    segments.append(AgeSegment(age_name="Dark Age", start_s=0.0, end_s=feudal_s))

    # 2. Feudal Age
    if castle_s is None or castle_s > duration:
        segments.append(AgeSegment(age_name="Feudal Age", start_s=feudal_s, end_s=duration))
        return segments

    segments.append(AgeSegment(age_name="Feudal Age", start_s=feudal_s, end_s=castle_s))

    # 3. Castle Age
    if imperial_s is None or imperial_s > duration:
        segments.append(AgeSegment(age_name="Castle Age", start_s=castle_s, end_s=duration))
        return segments

    segments.append(AgeSegment(age_name="Castle Age", start_s=castle_s, end_s=imperial_s))

    # 4. Imperial Age
    segments.append(AgeSegment(age_name="Imperial Age", start_s=imperial_s, end_s=duration))

    return segments


def filter_events_by_age(
    events: list[dict[str, Any]] | None,
    segments: list[AgeSegment],
) -> dict[str, list[dict[str, Any]]]:
    """Bucket events into their respective Ages based on age segments.

    Guard Clauses:
        - If events is None or empty, returns empty lists for all standard ages.
        - If segments is empty, all events are assigned to 'Dark Age'.

    Args:
        events: List of event dictionaries, each containing 'timestamp_s'.
        segments: List of AgeSegment defining chronological boundaries.

    Returns:
        dict[str, list[dict]]: Map of age names to their corresponding event lists.
    """
    age_buckets: dict[str, list[dict[str, Any]]] = {
        "Dark Age": [],
        "Feudal Age": [],
        "Castle Age": [],
        "Imperial Age": [],
    }

    if not events:
        return age_buckets

    if not segments:
        age_buckets["Dark Age"] = list(events)
        return age_buckets

    for event in events:
        t = float(event.get("timestamp_s", 0.0))
        placed = False

        for i, seg in enumerate(segments):
            is_last = (i == len(segments) - 1)
            end_bound = seg.end_s if seg.end_s is not None else float("inf")

            if is_last:
                if seg.start_s <= t <= end_bound:
                    age_buckets.setdefault(seg.age_name, []).append(event)
                    placed = True
                    break
            else:
                if seg.start_s <= t < end_bound:
                    age_buckets.setdefault(seg.age_name, []).append(event)
                    placed = True
                    break

        # Fallback if beyond all segments
        if not placed:
            age_buckets.setdefault(segments[-1].age_name, []).append(event)

    return age_buckets


def get_age_at_timestamp(timestamp_s: float, segments: list[AgeSegment]) -> str:
    """Return the name of the Age active at a specific timestamp.

    Guard Clauses:
        - If segments is empty, defaults to 'Dark Age'.
        - If timestamp_s is negative, defaults to 'Dark Age'.

    Args:
        timestamp_s: Timestamp in seconds.
        segments: List of AgeSegment.

    Returns:
        str: Name of the active Age.
    """
    if not segments or timestamp_s < 0.0:
        return "Dark Age"

    for i, seg in enumerate(segments):
        is_last = (i == len(segments) - 1)
        end_bound = seg.end_s if seg.end_s is not None else float("inf")
        if is_last:
            if seg.start_s <= timestamp_s <= end_bound:
                return seg.age_name
        else:
            if seg.start_s <= timestamp_s < end_bound:
                return seg.age_name

    return segments[-1].age_name
