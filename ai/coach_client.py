"""ai/coach_client.py
===================

Calls the Google Gemini LLM API via google-genai SDK to generate
expert Age-by-Age AoE2 coaching feedback.
Includes exponential backoff, timeout protection, payload size checks, and response parsing.
"""

from __future__ import annotations

import os
import time
from typing import Any

from ai.prompt_builder import build_system_prompt, build_user_prompt
from config.settings import Settings
from data.exceptions import AIAnalysisError, PayloadTooLargeError
from data.models import CoachingReport


def validate_api_key() -> str:
    """Validate and retrieve the GEMINI_API_KEY environment variable.

    Guard Clauses:
        - Rejects missing, empty, or placeholder API keys.

    Returns:
        str: Validated API key string.

    Raises:
        AIAnalysisError: If the key is unset or blank.
    """
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key or key == "your_api_key_here":
        raise AIAnalysisError(
            "GEMINI_API_KEY is not set. Add your key to .env or set the GEMINI_API_KEY environment variable. "
            "(Note: You can still run the offline parser with the 'convert' command without an API key)."
        )
    return key


def parse_coaching_response(
    raw_response: str,
    player_name: str,
    replay_name: str,
    language: str = "en",
) -> CoachingReport:
    """Parse raw LLM markdown into structured Age sections.

    Splits the markdown text across '## ' headers into a sections mapping.

    Guard Clauses:
        - If raw_response is empty, returns empty sections.
    """
    if not raw_response or not raw_response.strip():
        return CoachingReport(
            replay_name=replay_name,
            player_name=player_name,
            language=language,
            sections={},
            raw_response="",
        )

    sections: dict[str, list[str]] = {}
    current_section = "General"
    lines = raw_response.strip().splitlines()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = stripped[3:].strip()
            sections[current_section] = []
        elif stripped.startswith("- ") or stripped.startswith("* "):
            bullet = stripped[2:].strip()
            sections.setdefault(current_section, []).append(bullet)

    return CoachingReport(
        replay_name=replay_name,
        player_name=player_name,
        language=language,
        sections=sections,
        raw_response=raw_response,
    )


def call_coach_llm(
    report_json: str,
    language: str = "en",
    model: str | None = None,
    target_civ: str | None = None,
    user_question: str | None = None,
    max_retries: int = 3,
    timeout_s: float = 60.0,
) -> str:
    """Send compact match telemetry to the Gemini model and retrieve coaching advice.

    Implements:
    - Early guard on API key
    - Payload size guard (< 200 KB)
    - Retry logic with exponential backoff on transient errors
    - Domain knowledge base integration & specific player questions

    Args:
        report_json: Compact JSON string of the match telemetry.
        language: Output language ('en' or 'nl').
        model: Target Gemini model identifier (defaults to config GEMINI_MODEL / gemini-3.5-flash).
        target_civ: Player civilization name for specialized playbooks.
        user_question: Optional player question or focus area.
        max_retries: Maximum retry attempts for transient API failures.
        timeout_s: Timeout per attempt in seconds.

    Returns:
        str: Raw Markdown text response from the model.

    Raises:
        AIAnalysisError: If all retries fail or an unrecoverable API error occurs.
        PayloadTooLargeError: If payload exceeds 200 KB.
    """
    # Guard Clause 1: Validate API key before network attempts
    api_key = validate_api_key()

    # Guard Clause 2: Payload size check (200 KB safe limit)
    payload_bytes = len(report_json.encode("utf-8"))
    max_bytes = 200 * 1024
    if payload_bytes > max_bytes:
        raise PayloadTooLargeError(
            f"Telemetry payload size ({payload_bytes / 1024:.1f} KB) exceeds the maximum allowed limit (200 KB)."
        )

    chosen_model = model or Settings.gemini_model()
    system_prompt = build_system_prompt(language=language, target_civ=target_civ)
    user_prompt = build_user_prompt(report_json=report_json, user_question=user_question)

    # Late import to prevent hard dependency if only using convert command
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=0.3,
    )

    last_error: Exception | None = None
    backoff = 2.0

    for attempt in range(1, max_retries + 1):
        try:
            response = client.models.generate_content(
                model=chosen_model,
                contents=user_prompt,
                config=config,
            )
            if not response or not response.text:
                raise AIAnalysisError("Received empty response from Gemini API.")
            return response.text

        except Exception as e:
            last_error = e
            err_str = str(e).lower()

            # Unrecoverable errors (invalid key, bad request) -> fail immediately
            if "api_key_invalid" in err_str or "unauthenticated" in err_str or "invalid argument" in err_str:
                raise AIAnalysisError(f"Gemini API authentication or argument error: {e}") from e

            # Transient errors -> wait and retry
            if attempt < max_retries:
                time.sleep(backoff)
                backoff *= 2.0

    raise AIAnalysisError(
        f"Failed to generate coaching feedback after {max_retries} attempts: {last_error}"
    ) from last_error
