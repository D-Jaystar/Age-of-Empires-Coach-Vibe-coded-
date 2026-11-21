"""ai/prompt_builder.py
=====================

Constructs rigorous, domain-specific System and User prompts for LLM coaching generation.
Enforces zero hallucination, numerical AoE2 benchmarks, civilization playbooks,
few-shot training examples, and custom player focus questions.
"""

from __future__ import annotations

import json
from typing import Optional

from ai.knowledge_base import (
    BUILD_ORDER_BENCHMARKS,
    FEW_SHOT_COACHING_EXAMPLE_EN,
    FEW_SHOT_COACHING_EXAMPLE_NL,
    TACTICAL_ADAPTATION_RULES,
)
from data.civ_database import format_civ_summary, format_matchup_overview, load_civilizations


def build_system_prompt(language: str = "en", target_civ: str | None = None) -> str:
    """Build the comprehensive System Prompt configuring the LLM as an expert AoE2 coach."""
    lang = language.lower().strip() if language else "en"
    is_dutch = (lang == "nl")

    if is_dutch:
        lang_instruction = (
            "BELANGRIJKE TAALINSTRUCTIE:\n"
            "Schrijf je volledige coaching analyse in natuurlijk, deskundig en direct NEDERLANDS.\n"
            "Behoud herkenbare vaktermen in het Engels (zoals 'Dark Age', 'Feudal Age', 'Castle Age', 'Imperial Age', "
            "'Scouts opening', 'Archers', 'TC idle time', 'Loom', 'Wheelbarrow', 'Bloodlines', 'eAPM', 'Fletching', 'Bagains')."
        )
        few_shot = FEW_SHOT_COACHING_EXAMPLE_NL
    else:
        lang_instruction = (
            "LANGUAGE INSTRUCTION:\n"
            "Write your entire coaching analysis in clear, direct, competitive English."
        )
        few_shot = FEW_SHOT_COACHING_EXAMPLE_EN

    # Civilization-specific playbook highlight from database
    civ_section = ""
    if target_civ:
        civ_section = format_civ_summary(target_civ)
    else:
        db = load_civilizations()
        civ_summaries = []
        for c_name, c_info in list(db.items())[:8]:
            civ_summaries.append(f"- **{c_name}**: Focus: {c_info.get('focus', 'General')} | Restriction: {c_info.get('tech_restrictions', 'None')}")
        civ_section = "\n### GENERAL CIVILIZATION PLAYBOOKS:\n" + "\n".join(civ_summaries)

    return f"""You are an elite, top-tier Age of Empires II: Definitive Edition (AoE2:DE) coach and competitive analyst.
You review recorded game telemetry to give sharp, concrete, and highly actionable coaching advice.

{lang_instruction}

{TACTICAL_ADAPTATION_RULES}

### STRICT COACHING PRINCIPLES:
1. ZERO HALLUCINATION:
   - Only reference timings, numbers, unit lines, idle gaps, and build orders that are EXPLICITLY present in the JSON telemetry report.
   - If a metric is null or missing, state that clearly—do NOT invent or guess numbers.
   - NEVER suggest units or upgrades the civ does NOT possess in their tech tree (e.g. Bulgarians DO NOT have Paladins, Britons DO NOT have Bloodlines, Mayans DO NOT have Cavalry).
2. NO BASELESS ASSUMPTIONS - EVALUATE TACTICAL COUNTERS CONSTRUCTIVELY:
   - In Castle and Imperial Age, do NOT assume that teching into secondary units (e.g. Infantry or ranged upgrades) is a "mistake".
   - Recognize that against enemy Halberdiers/Pikemen, switching to Infantry (such as Bulgarian Two-Handed Swordsmen with Bagains) is standard high-level adaptation!
   - Recognize that Fletching, Bodkin Arrow, and Bracer buff defensive Castles, Kreposts, and Town Centers, protecting Trebuchets from being rushed down.
   - On hybrid maps like Four Lakes, recognize that booming on deep fish and clicking Castle Age at ~14:58 with 0 Feudal farms is a known, effective Fast Castle strategy, NOT an economic failure!
3. CAUSE AND EFFECT:
   - For every genuine gameplay flaw (such as Dark Age TC idle gaps, floating unspent resources, or missing blacksmith armor when taking fights), explain *what* happened and *why* it affected the player's timings.
4. CONCRETE BENCHMARKS & BUILD-ORDER CHECKLISTS:
   - Provide concrete target numbers and mini checklists for Dark Age.
   - Give farm-count milestones (e.g. "Aim for ~14-16 active farms before clicking Castle Age on standard land maps").
5. CONTEXT AWARENESS:
   - Check map characteristics (Land, Hybrid, or Water).
   - Check if this is a Team Game (multiple opponents) vs 1v1. In Team Games, players often face multiple unit lines (e.g. mass halbs + cavalry) and must adapt.
6. TONE:
   - Direct, constructive, practical, and punchy. Avoid generic fluff. Respect the player's tactical decisions.

{civ_section}

{BUILD_ORDER_BENCHMARKS}

{few_shot}

### REQUIRED OUTPUT FORMAT:
For EVERY age reached in the match (Dark Age, Feudal Age, Castle Age, and Imperial Age if reached):
You MUST provide:
1. A Markdown table with EXACTLY 3 Tips on the left and 3 Tops on the right:
   | 💡 3 Tips (Verbeterpunten / Areas to Improve) | 🏆 3 Tops (Sterke Punten / Key Strengths) |
   | :--- | :--- |
   | • **Tip 1:** [Concrete improvement with timing/number] | • **Top 1:** [Standout execution or clean benchmark] |
   | • **Tip 2:** [Concrete improvement with timing/number] | • **Top 2:** [Standout execution or clean benchmark] |
   | • **Tip 3:** [Concrete improvement with timing/number] | • **Top 3:** [Standout execution or clean benchmark] |
2. Followed by bullet points and mini-checklists explaining the tactical cause-and-effect, farm engine pacing, military composition synergy, and situational counters.

Structure your response with these exact top-level section headers:
## Dark Age
## Feudal Age
## Castle Age
## Imperial Age (ONLY include if the match reached Imperial Age according to the telemetry; otherwise omit it!)
## Player Focus Point (Include if a specific player question was asked)
"""


def build_user_prompt(report_json: str, user_question: Optional[str] = None) -> str:
    """Build the User Prompt containing match telemetry and optional custom player questions.

    Guard Clauses:
        - If report_json is empty or whitespace, raises ValueError.

    Args:
        report_json: Compact JSON string of the ParsedReplayReport.
        user_question: Optional specific question or focus area provided by the user.

    Returns:
        str: User prompt ready for the LLM.
    """
    cleaned = report_json.strip() if report_json else ""
    if not cleaned:
        raise ValueError("report_json cannot be empty.")

    custom_question_section = ""
    if user_question and user_question.strip():
        custom_question_section = f"""
### SPECIFIC PLAYER QUESTION / FOCUS POINT:
The player specifically requested advice on the following topic:
"{user_question.strip()}"
Please address this question directly in a dedicated `## Player Focus Point` section in your response!
"""

    matchup_section = ""
    context_section = ""
    try:
        data = json.loads(cleaned)
        meta = data.get("metadata", {})
        gmode = meta.get("gamemode")
        mpos = meta.get("map_position")
        if gmode or mpos:
            context_section = f"""
### MATCH FORMAT & ROLE CONTEXT:
- **Game Mode:** {gmode or 'Standard Match'}
- **Map Position:** {mpos or 'Unspecified'}
- **Strategic Impact:**
  * Pocket role: Prioritize fast Castle Age timing, cavalry mobility, economy boom, and flank assistance. Do NOT penalize absence of early Feudal aggression.
  * Flank role: Prioritize early Feudal aggression, archery range/scout timing, forward walling, and surviving early enemy pressure.
  * 1v1 role: Direct matchup tempo, resource denial, and proactive counters.
"""
        tp_player = data.get("target_player", {}).get("player", {})
        tp_name = tp_player.get("name", "Analyzed Player")
        tp_civ = tp_player.get("civilization", "Unknown")
        opps = data.get("opponents", [])
        if opps:
            opp_list = [
                {"name": o.get("name") or f"Opponent {i}", "civilization": o.get("civilization", "Unknown")}
                for i, o in enumerate(opps, 1)
            ]
            matchup_section = format_matchup_overview(tp_name, tp_civ, opp_list)
    except Exception:
        pass

    return f"""Here is the deterministic match telemetry and heuristic analysis for an Age of Empires II match:

{context_section}
{matchup_section}

### RAW MATCH TELEMETRY:
```json
{cleaned}
```
{custom_question_section}
Please review this telemetry thoroughly and provide your comprehensive, Age-by-Age coaching report following the instructions and required Markdown sections. Focus heavily on identifying actionable improvements for the analyzed player."""
