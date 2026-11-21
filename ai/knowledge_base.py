"""ai/knowledge_base.py - Build order benchmarks, tactical rules, and few-shot examples."""

from __future__ import annotations

BUILD_ORDER_BENCHMARKS = """
### STANDARD BUILD ORDER TIMING BENCHMARKS (1x Speed):
1. 19-Pop Scouts (Franks, Magyars, Mongols):
   - Feudal Click: ~07:05 (425s) | Feudal Arrival: ~09:15 (555s)
   - Setup: 6 Sheep, 3 Wood, 1 Boar #1, 4 Berries, 1 Boar #2, 3 Food under TC, Loom, Click Feudal.
   - Gold: 0 on gold in Dark Age! (Gold is mined only later for Bloodlines or Castle Age).

2. 20-Pop Archers (Britons, Ethiopians, Saracens):
   - Feudal Click: ~07:30 (450s) | Feudal Arrival: ~09:40 (580s)
   - Setup: 6 Sheep, 4 Wood, 1 Boar #1, 4 Berries, 1 Boar #2, 3 Gold (Mining Camp), Loom, Click Feudal.
   - Feudal: 2 Archery Ranges + Blacksmith immediately. Research Fletching.

3. 21-Pop Men-at-Arms into Archers:
   - Feudal Click: ~07:55 (475s) | Feudal Arrival: ~10:05 (605s)
   - Setup: Barracks built at ~60% Dark Age. Queue 3 Militia before aging up.
   - Feudal: Research Man-at-Arms immediately upon reaching Feudal (~10:05).

4. Fast Castle (Arena / Hybrid Water Boom):
   - Feudal Click: ~09:30–10:00 (or ~08:30 on water) | Castle Click: ~12:30–14:50
   - Setup: Minimal military; build Market + Blacksmith (or Docks/fish), click Castle Age immediately.
"""

TACTICAL_ADAPTATION_RULES = """
### CRITICAL COACHING PRINCIPLES: ZERO HALLUCINATIONS & NO FALSE ASSUMPTIONS:

1. STRICT TECH-TREE VERIFICATION:
   - NEVER suggest or critique a unit, technology, or building that the player's civilization CANNOT have!
   - Examples of banned hallucinations:
     * Bulgarians DO NOT have Paladin (Cavalier is their maximum). NEVER suggest Paladin for Bulgarians!
     * Bulgarians DO NOT have Crossbowman or Arbalester.
     * Britons DO NOT have Bloodlines or Thumb Ring.
     * Franks DO NOT have Bloodlines or Arbalester.
     * Mayans DO NOT have Cavalry or Gunpowder.
     * Teutons DO NOT have Husbandry.
     * Byzantines DO NOT have Bloodlines or Blast Furnace.
     * Poles & Berbers DO NOT have Paladin.

2. AVOID ASSUMPTIONS: RECOGNIZE SITUATIONAL COUNTERS & TACTICAL ADAPTATIONS:
   - In AoE2, players MUST adapt to opponent unit compositions. Never criticize strategic adaptation as a "mistake"!
   - Tactical Counter Examples:
     * Anti-Cavalry Reaction: If opponents make mass Halberdiers, teching into Infantry (e.g. Bulgarians getting free Two-Handed Swordsmen + Bagains +5 armor) is an EXPERT TACTICAL COUNTER, not a lack of focus!
     * Ranged Techs for Castles & Kreposts: Upgrades like Fletching, Bodkin Arrow, and Bracer increase the range, attack, and arrow count of Town Centers, Castles, Kreposts, and Towers to protect Trebuchets and prevent Halberdier-dives.
     * Fast Castle off Pond Fish: On hybrid maps (Four Lakes), relying on fish food and delaying land farms in Feudal Age to click Castle Age at 14:00–15:00 is a standard, highly effective Fast Castle strategy.
     * Team Game Dynamics: In team games (multiple opponents), players face diverse armies and must adapt. Do not judge team games by dogmatic 1v1 Arabia standards.

3. CONSTRUCTIVE COACHING TONE:
   - Frame observations with context: "You adapted by adding infantry upgrades to counter enemy Halberdiers, capitalizing on Bulgarians' free Militia upgrades and Bagains."
   - Do NOT say "you made a mistake by deviating from your core unit line" unless the player had zero army or destroyed their economy.
"""

FEW_SHOT_COACHING_EXAMPLE_NL = """
### VOORBEELD VAN EEN GOED COACHING RAPPORT (NL):

## Dark Age
* **Feudal Click Timing:** Je klikte naar Feudal Age op 08:45 (525s) met 21 villagers. Voor een Frank Scouts opening mik je op 07:05–07:15.
* **TC Idle Time:** Je hebt 48.5 seconden totale idle TC time opgelopen, met een piek van 35s rond 04:30. Zorg dat je zwijn naar het TC rent vóórdat je schapen op zijn.
* **Vroege Goudverzameling:** Je stuurde 3 villagers naar goud in Dark Age. Bij een Scouts rush heb je 0 goud nodig; die hadden op hout of bessen moeten staan voor eerdere boerderijen.

## Feudal Age
* **Opening:** 1 Stable geopend voor Scouts. Goede keuze voor Franken.
* **Boerderijen:** Eerste boerderij pas op 13:20. Zorg dat je rond minuut 10:00 je eerste boerderijen plaatst om je voedselinkomen voor Castle Age op te bouwen.
"""

FEW_SHOT_COACHING_EXAMPLE_EN = """
### EXAMPLE OF A STRONG COACHING REPORT (EN):

## Dark Age
* **Feudal Click Timing:** Clicked Feudal Age at 08:45 (525s) with 21 villagers. For a Frank Scouts opening, target 07:05–07:15.
* **TC Idle Time:** 48.5s total idle time, peaking around 04:30 near your first boar lure. Lure earlier to prevent gaps.
* **Resource Balance:** 3 villagers on gold in Dark Age. Scout openings need 0 gold in Dark Age; keep them on wood/food.

## Feudal Age
* **Opening:** 1 Stable Scouts. Good civ synergy with Frank cavalry HP bonus.
* **Farms:** First farm delayed until 13:20. Begin seeding farms around 10:00 to fuel Castle Age transition.
"""
