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
### VOORBEELD VAN EEN GOED COACHING RAPPORT MET 3 TIPS & 3 TOPS (NL):

## Dark Age

| 💡 3 Tips (Verbeterpunten) | 🏆 3 Tops (Sterke Punten) |
| :--- | :--- |
| • **Tip 1:** Breng je Feudal click omlaag naar ~07:15 (435s) in plaats van 08:35 (515s) voor een vlottere opening. | • **Top 1:** Vrijwel vlekkeloze TC uptime met slechts 0.6s totale idle time (99.9% uptime). |
| • **Tip 2:** Lok je schapen direct onder het TC (binnen 5 tiles) om villager looptijd te minimaliseren. | • **Top 2:** Loom perfect getimed op 06:53 vlak voor het klikken, waardoor je vils continu produceerden. |
| • **Tip 3:** Op Four Lakes: plaats je shoreline Dock eerder rond 03:15 voor eerdere deep-fish inkomsten. | • **Top 3:** Uitstekende resourcebalans met 0 vils verspild op goud/steen tijdens je Dark Age food rush. |

## Feudal Age

| 💡 3 Tips (Verbeterpunten) | 🏆 3 Tops (Sterke Punten) |
| :--- | :--- |
| • **Tip 1:** Start je eerste boerderij rond minuut 10:00 om je landbouwmotor tijdig op te starten. | • **Top 1:** Supersnelle Castle Age click op 14:58 (898s) waarmee je de tegenstanders voorbleef. |
| • **Tip 2:** Onderzoek Wheelbarrow rond villager 35-40 in plaats van uitstellen tot minuut 22:38 (53 vils). | • **Top 2:** Slim gebruikgemaakt van deep fish macro om razendsnel naar Castle Age te gaan. |
| • **Tip 3:** Voeg tijdig een tweede productiegebouw toe om je militaire eenheden te continueren. | • **Top 3:** Strakke opening discipline met 2 Stables al geplaatst voor een onmiddellijke Knight power-spike. |
"""

FEW_SHOT_COACHING_EXAMPLE_EN = """
### EXAMPLE OF A STRONG COACHING REPORT WITH 3 TIPS & 3 TOPS (EN):

## Dark Age

| 💡 3 Tips (Areas to Improve) | 🏆 3 Tops (Key Strengths) |
| :--- | :--- |
| • **Tip 1:** Accelerate your Feudal click towards ~07:15 (435s) instead of 08:35 (515s) for cleaner tempo. | • **Top 1:** Outstanding TC uptime with only 0.6s total idle time (99.9% active queue). |
| • **Tip 2:** Harvest sheep directly underneath the TC (< 5 tiles) to eliminate villager walking lag. | • **Top 2:** Loom delayed appropriately until 06:53 right before clicking, keeping vils pumping. |
| • **Tip 3:** On Four Lakes: place your Dock earlier at ~03:15 to access deep fish before aging up. | • **Top 3:** Zero early idle gold mining, prioritizing wood and food for your core opening. |

## Feudal Age

| 💡 3 Tips (Areas to Improve) | 🏆 3 Tops (Key Strengths) |
| :--- | :--- |
| • **Tip 1:** Seed your first farm around minute 10:00 to kickstart your land farming engine. | • **Top 1:** Lightning-fast Castle click at 14:58 (898s), outpacing all opponents to the next age. |
| • **Tip 2:** Research Wheelbarrow at 35-40 villagers rather than delaying until 22:38 (53 vils). | • **Top 2:** Excellent water boom execution, funding Castle click entirely off deep fish. |
| • **Tip 3:** Add a secondary production building early to sustain military tempo. | • **Top 3:** Proactive infrastructure with 2 Stables queued early to hit hard with Knights. |
"""
