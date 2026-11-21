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

### Analyse & Tactische Diepgang:
* **Feudal Click Timing & Macro:** Je klikte naar Feudal Age op 08:35 (515s) met 23 villagers. Dit is iets aan de trage kant voor een standaard Scouts opening (streef naar ~07:15–07:30 met 19-20 pop). Je had voldoende voedsel, maar er zat vertraging in de overgang tussen je schapen en je tweede zwijn.
* **TC Idle Time & Boar Lure:** Je had een uitstekende TC uptime met slechts 0.6s totale idle time, wat uitzonderlijk goed is. Wel oogstte je schapen op 7.9 tiles afstand in plaats van direct onder het Town Center, wat leidde tot onnodige wandeltijd voor je villagers.
* **Dock Plaatsing op Water/Hybrid:** Op Four Lakes werd je eerste Dock pas geplaatst op 07:14 en de eerste Fishing Ship op 08:32. Hierdoor miste je het vroege diepzee-visvoordeel waarmee je je Feudal click aanzienlijk had kunnen versnellen.
* **Resourcebalans:** Met 56% voedsel en 44% hout had je een strakke balans zonder verspilling op goud of steen.

> 📌 **Snelle Samenvatting (Tips & Tops):**
> 
> | 💡 3 Tips (Verbeterpunten) | 🏆 3 Tops (Sterke Punten) |
> | :--- | :--- |
> | • **Tip 1:** Breng je Feudal click omlaag naar ~07:15 (435s) met 19-20 pop. | • **Top 1:** Vrijwel vlekkeloze TC uptime met slechts 0.6s totale idle time (99.9%). |
> | • **Tip 2:** Lok je schapen direct onder het TC (< 5 tiles) om looptijd te schrappen. | • **Top 2:** Loom uitgesteld tot 06:53 vlak voor de click, waardoor je queue vol bleef. |
> | • **Tip 3:** Plaats je shoreline Dock rond 03:15 om deep fish tijdig te benutten. | • **Top 3:** Uitstekende resourcebalans met 0 vils verspild op goud/steen. |

## Feudal Age

### Analyse & Tactische Diepgang:
* **Opening & Militaire Productie:** Je opende met 2 Stables voor Scouts/Cavalier transitie. Je trainde 13 eenheden in Feudal Age, wat prima is voor map presence. Wel duurde het even voordat de tweede Stable daadwerkelijk eenheden produceerde.
* **Boerderijenmotor & Vis Economie:** Je bouwde 0 boerderijen in Feudal Age en financierde je Castle click volledig via visvoedsel. Dit gaf je een snelle 14:58 Castle Age click, maar liet je landbouwinfrastructuur kwetsbaar achter zodra visvijvers uitgeput raakten.
* **Wheelbarrow Timing:** Wheelbarrow werd uitgesteld tot 22:38 (53 vils). Na aankomst in Castle Age had dit rond minuut 16:00–17:00 onderzocht moeten worden.

> 📌 **Snelle Samenvatting (Tips & Tops):**
> 
> | 💡 3 Tips (Verbeterpunten) | 🏆 3 Tops (Sterke Punten) |
> | :--- | :--- |
> | • **Tip 1:** Start rond 10:00 je eerste boerderijen als back-up voor je vismacro. | • **Top 1:** Supersnelle Castle click op 14:58 (898s), sneller dan alle rivalen. |
> | • **Tip 2:** Onderzoek Wheelbarrow rond vil 35-40 ipv uitstellen tot minuut 22:38. | • **Top 2:** Slim gebruikgemaakt van deep fish macro voor tempo-voordeel. |
> | • **Tip 3:** Laat beide Stables continu produceren zonder idle gaps. | • **Top 3:** Proactieve infrastructuur met 2 Stables tijdig geplaatst voor Knights. |
"""

FEW_SHOT_COACHING_EXAMPLE_EN = """
### EXAMPLE OF A STRONG COACHING REPORT (EN):

## Dark Age

### Tactical Analysis & Core Observations:
* **Feudal Click Timing & Macro:** You clicked Feudal Age at 08:35 (515s) with 23 villagers. This is slightly behind the 19-20 pop target (~07:15–07:30) for a Scouts opening. You gathered ample food, but transitions between sheep and boar lured were slightly sluggish.
* **TC Idle Time & Herdable Placement:** Outstanding TC uptime with only 0.6s total idle time. However, sheep were harvested 7.9 tiles away from the TC rather than directly underneath it, causing unnecessary villager walking delays.
* **Dock Timing on Hybrid Map:** On Four Lakes, your first Dock went up late at 07:14 and first Fishing Ship at 08:32, forfeiting early deep-fish gather rates that could have accelerated your Feudal timing.
* **Resource Balance:** 56% Food / 44% Wood with zero wasted villagers on gold or stone during your Dark Age food rush.

> 📌 **Quick Takeaways (Tips & Tops):**
> 
> | 💡 3 Tips (Areas to Improve) | 🏆 3 Tops (Key Strengths) |
> | :--- | :--- |
> | • **Tip 1:** Accelerate your Feudal click towards ~07:15 (435s) at 19-20 population. | • **Top 1:** Outstanding TC uptime with only 0.6s total idle time (99.9% active queue). |
> | • **Tip 2:** Harvest sheep directly underneath the TC (< 5 tiles) to eliminate walking lag. | • **Top 2:** Loom delayed appropriately until 06:53 right before clicking. |
> | • **Tip 3:** Place your shoreline Dock at ~03:15 to access deep fish before aging up. | • **Top 3:** Zero early idle gold mining, prioritizing wood and food for your core opening. |

## Feudal Age

### Tactical Analysis & Core Observations:
* **Opening & Military Output:** You opened with 2 Stables and produced 13 units in Feudal Age. Good map pressure, though your second Stable sat idle briefly before ramping up production.
* **Farming Engine vs Water Boom:** You built 0 farms in Feudal Age, funding your Castle click entirely off deep fish. While this gave you a rapid 14:58 Castle Age click, it left you with zero land farming infrastructure once pond fish ran dry.
* **Wheelbarrow Timing:** Wheelbarrow was delayed until 22:38 at 53 villagers. Researching it shortly after arriving in Castle Age (~16:00–17:00) boosts villager gather efficiency.

> 📌 **Quick Takeaways (Tips & Tops):**
> 
> | 💡 3 Tips (Areas to Improve) | 🏆 3 Tops (Key Strengths) |
> | :--- | :--- |
> | • **Tip 1:** Seed farms around minute 10:00 to transition smoothly off natural fish. | • **Top 1:** Blazing Castle click at 14:58 (898s), outpacing all opponents. |
> | • **Tip 2:** Research Wheelbarrow at 35-40 villagers rather than delaying to 22:38. | • **Top 2:** Excellent water fish macro converted into immediate Castle tempo. |
> | • **Tip 3:** Keep production buildings active without queue gaps. | • **Top 3:** Proactive military infrastructure with 2 Stables ready for Knights. |
"""
