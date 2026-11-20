"""ai/knowledge_base.py
======================

Domain knowledge base and reference training data for the AoE2 AI Coach.
Contains civilization playbooks, build-order benchmarks, counter-matrix rules,
and few-shot coaching examples in both English and Dutch.
"""

from __future__ import annotations

CIVILIZATION_PLAYBOOKS: dict[str, dict[str, str]] = {
    "Bulgarians": {
        "bonuses": "Militia-line upgrades are FREE automatically upon aging up (Man-at-Arms, Long Swordsman, Two-Handed Swordsman); Blacksmith and Siege Workshop upgrades cost -50% food; Town Centers cost -50% stone (only 50 stone); can build Kreposts (mini-castles for 350 stone).",
        "ideal_opening": "19–20 pop Scouts or Men-at-Arms (free M@A upgrade!).",
        "castle_age_core": "Stirrups Knights (+33% attack speed) or Krepost drops, transitioning into Konniks or free Long Swordsmen + cheap Siege.",
        "essential_upgrades": "Stirrups (Castle Age Unique Tech: +33% attack speed for Scout line and Knight line!), Scale/Chain Barding Armor, Forging/Iron Casting (-50% food cost!). In Imperial: Bagains (+5 armor for Militia-line) makes Two-Handed Swordsmen demolish enemy Halberdiers.",
        "tech_restrictions": "CRITICAL: NO PALADIN (Cavalier is their maximum cavalry upgrade; NEVER recommend Paladin!); NO Crossbowman or Arbalester (Archer line ends at Archer); NO Ring Archer Armor; NO Treadmill Crane.",
        "common_pitfalls": "Hallucinating that Bulgarians have Paladin (they DO NOT); neglecting the free Militia upgrades; forgetting that Castles and Kreposts benefit from Bodkin Arrow & Bracer; not using Bagains Two-Handed Swordsmen to counter mass Halberdiers.",
    },
    "Franks": {
        "bonuses": "Free Farm upgrades (Mill), +20% Cavalry HP starting in Feudal, Castles cost -25%, faster Foragers.",
        "ideal_opening": "19–20 pop Scouts.",
        "castle_age_core": "Heavy Knight production (2–3 Stables), expanding to 3 Town Centers.",
        "essential_upgrades": "Scale Barding Armor -> Chain Barding Armor, Forging -> Iron Casting. In Imp: Paladin, Chivalry (Stables work 40% faster).",
        "tech_restrictions": "NO Bloodlines (compensated by +20% HP civ bonus); NO Arbalester; NO Ring Archer Armor; NO Bracer; NO Siege Ram.",
        "common_pitfalls": "Mining early gold with Scouts; switching to non-cavalry units without reason.",
    },
    "Britons": {
        "bonuses": "Archery Ranges work 20% faster, Foot archers get +1 range in Castle Age (+2 in Imp), Shepherds work 25% faster.",
        "ideal_opening": "20–21 pop Straight Archers or Men-at-Arms into Archers.",
        "castle_age_core": "Double-Range Crossbowmen + Bodkin Arrow, supported by Ballistics and Siege/Monks.",
        "essential_upgrades": "Fletching (Feudal), Bodkin Arrow (Castle), Padded Archer Armor, Ballistics, Bracer, Chemistry.",
        "tech_restrictions": "NO Bloodlines; NO Thumb Ring; NO Paladin; NO Hussar; NO Siege Onager; NO Bombard Cannon.",
        "common_pitfalls": "Skipping early Archery Range production; delaying Fletching before fights; letting knights get close without pikes.",
    },
    "Magyars": {
        "bonuses": "Free melee Blacksmith attack upgrades (Forging, Iron Casting, Blast Furnace), Scouts cost -15%.",
        "ideal_opening": "18–20 pop Scouts (very fast aggressive scout rush).",
        "castle_age_core": "Knights or Cavalry Archers with Bloodlines and Recurve Bow.",
        "essential_upgrades": "Bloodlines, Husbandry, Scale/Chain Barding Armor (attack upgrades are free!). In Imp: Paladin, Recurve Bow (+1 range/attack for Cav Archers).",
        "tech_restrictions": "NO Camel; NO Siege Ram; NO Hand Cannoneer; NO Squires; NO Plate Mail Armor.",
        "common_pitfalls": "Over-investing in late Feudal scouts instead of clicking up to Castle Age for Knights.",
    },
    "Mayans": {
        "bonuses": "Longer-lasting resources (+15%), extra villager start, cheaper archers (-10% Feudal, -20% Castle, -30% Imp).",
        "ideal_opening": "21–22 pop Archers or Men-at-Arms into Archers.",
        "castle_age_core": "Plumed Archers or Crossbowmen combined with Eagle Warriors.",
        "essential_upgrades": "Fletching/Bodkin Arrow, Scale/Chain Mail Armor for Eagles, Squires, El Dorado (+40 HP for Eagles).",
        "tech_restrictions": "NO Stables / Cavalry; NO Gunpowder; NO Champions; NO Siege Onager.",
        "common_pitfalls": "Neglecting Eagle upgrades; building cavalry buildings (Mayans have no stables).",
    },
    "Mongols": {
        "bonuses": "Hunters work 40% faster, Scout line +2 LOS, Cavalry Archers fire 25% faster.",
        "ideal_opening": "18–19 pop Fast Scouts (rapid hunt harvesting gives early food surplus).",
        "castle_age_core": "Steppe Lancers or early Castle into Mangudai + Siege.",
        "essential_upgrades": "Bloodlines, Scale Barding Armor, Husbandry, Drill (Siege moves 50% faster).",
        "tech_restrictions": "NO Paladin; NO Ring Archer Armor; NO Halberdier; NO Architecture; NO Plate Barding Armor.",
        "common_pitfalls": "Failing to capitalize on the early hunt speed; idling hunters after boars/deer are finished.",
    },
    "Saracens": {
        "bonuses": "Market commodity fee only 5%, Markets cost -100 wood, Archery Range units attack buildings +2.",
        "ideal_opening": "20–21 pop Archers or Market abuse Fast Castle.",
        "castle_age_core": "Crossbowmen tearing down buildings, Camel Riders against opponent cavalry.",
        "essential_upgrades": "Fletching/Bodkin Arrow, Scale/Chain Barding Armor for Camels.",
        "tech_restrictions": "NO Cavalier / Paladin; NO Halberdier; NO Shipwright; NO Bombard Tower.",
        "common_pitfalls": "Forgetting to utilize the 5% Market fee to balance economy for faster up-times.",
    },
    "Teutons": {
        "bonuses": "Farms cost -40%, Barracks/Stable units get +1 melee armor in Castle/Imp, Town Centers hold +10 units.",
        "ideal_opening": "20–21 pop Scouts or Men-at-Arms into Farms.",
        "castle_age_core": "Cheaper farm boom into heavy Knights with high melee armor + Siege.",
        "essential_upgrades": "Bloodlines, Scale/Chain Barding Armor, Iron Casting. In Imp: Paladin, Ironclad (+4 armor for siege).",
        "tech_restrictions": "NO Husbandry (Teuton cavalry is slower!); NO Thumb Ring; NO Bracer; NO Light Cavalry / Hussar.",
        "common_pitfalls": "Slow movement speed makes Teuton units vulnerable to kiting; lack of Husbandry requires good positioning.",
    },
    "Byzantines": {
        "bonuses": "Cheaper trash units (Pikemen, Skirmishers, Camels cost -25%), aging up to Imperial costs -33%, Town Watch free.",
        "ideal_opening": "20–21 pop defensive Skirmishers/Archers or Scouts.",
        "castle_age_core": "Counter-unit composition (cheap Camels vs Knights, cheap Skirms vs Crossbows) into fast Imperial Age.",
        "essential_upgrades": "Defensive armor upgrades (Chain Mail, Chain Barding, Leather Archer Armor).",
        "tech_restrictions": "NO Bloodlines; NO Blast Furnace; NO Siege Engineers; NO Parthian Tactics; NO Heavy Scorpion.",
        "common_pitfalls": "Over-committing to offensive attacks instead of taking cost-effective defensive trades and beating opponent to Imperial.",
    },
    "Lithuanians": {
        "bonuses": "+150 food start, Spearmen and Skirmishers move 10% faster, Knights/Leitis get +1 attack per Relic garrisoned (max +4).",
        "ideal_opening": "19–20 pop Scouts or Fast Castle.",
        "castle_age_core": "Relic hunting with Monks into heavy Knights/Leitis.",
        "essential_upgrades": "Bloodlines, Scale/Chain Barding Armor. In Imp: Paladin, Tower Shields (+2 pierce armor for spearmen/skirms).",
        "tech_restrictions": "NO Siege Engineers; NO Arbalester; NO Plate Mail Armor.",
        "common_pitfalls": "Neglecting Relic collection; losing relics to the opponent.",
    },
    "Berbers": {
        "bonuses": "Villagers move 10% faster, Stable units cost -15% in Castle Age (-20% in Imp), Ships move 10% faster.",
        "ideal_opening": "19–20 pop Scouts.",
        "castle_age_core": "Cheap mass Knights and Camel Riders, supported by Camel Archers.",
        "essential_upgrades": "Bloodlines, Scale/Chain Barding Armor, Kasbah (Castles work 25% faster).",
        "tech_restrictions": "NO Paladin; NO Arbalester; NO Parthian Tactics; NO Siege Onager; NO Halberdier.",
        "common_pitfalls": "Over-relying on gold units when gold runs low; forgetting that Berbers do not have Paladin.",
    },
    "Poles": {
        "bonuses": "Folwark replaces Mill (instantly deposits 8% of surrounding farms), Stone miners also generate gold, Villagers regenerate HP.",
        "ideal_opening": "19–20 pop Scouts or Folwark Fast Castle.",
        "castle_age_core": "Folwark farm boom into cheap Szlachta Privileges Knights (-60% gold cost!).",
        "essential_upgrades": "Bloodlines, Scale/Chain Barding Armor, Szlachta Privileges.",
        "tech_restrictions": "NO Paladin; NO Plate Barding Armor; NO Ring Archer Armor; NO Halberdier.",
        "common_pitfalls": "Failing to build farms touching the Folwark; assuming Poles have Paladin or final cavalry armor.",
    },
}

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
   - In Age of Empires II, players MUST adapt to what their opponents are building. Never criticize strategic adaptation as a "mistake" or "distraction"!
   - Tactical Counter Examples:
     * Anti-Cavalry Reaction: If opponents are making mass Spearmen / Pikemen / Halberdiers, teching into Infantry (e.g. Bulgarians getting free Two-Handed Swordsmen + Bagains +5 armor, or Long Swordsmen/Champions) is an EXPERT TACTICAL COUNTER, not a lack of focus!
     * Ranged Techs for Castles & Kreposts: Upgrades like Fletching, Bodkin Arrow, and Bracer increase the range, attack, and arrow count of Town Centers, Castles, Kreposts, and Towers. Players often research these to protect Trebuchets and prevent enemy Halberdiers from diving under Castles!
     * Fast Castle off Pond Fish: On hybrid maps (e.g. Four Lakes), relying on fish food and delaying land farms in Feudal Age to click Castle Age at 14:00–15:00 is a standard, highly effective build order. Do not criticize zero Feudal farms if the player successfully fast-castled off water!
     * Team Game Dynamics: In team games (multiple opponents), players face diverse armies and must coordinate roles or counter multiple threats. Do not judge team games by dogmatic 1v1 Arabia standards.

3. CONSTRUCTIVE COACHING TONE:
   - Frame observations with context: "You adapted by adding infantry upgrades—likely to counter enemy Halberdiers—which takes advantage of Bulgarians' free Militia upgrades and Bagains."
   - Do NOT say "you made a mistake by deviating from your core unit line" unless the player had zero army or destroyed their own economy.
"""

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

4. Fast Castle (Arena / Boom):
   - Feudal Click: ~09:30–10:00 (24–26 pop) | Castle Click: ~12:30 | Castle Arrival: ~15:10
   - Setup: Minimal military; build Market + Blacksmith in Feudal, click Castle Age immediately.
"""

FEW_SHOT_COACHING_EXAMPLE_NL = """
### VOORBEELD VAN EEN GOED COACHING RAPPORT (NL):

## Dark Age
* **Feudal Click Timing:** Je klikte naar Feudal Age op 08:45 (525s) met 21 villagers. Voor een Frank Scouts opening mik je op een 19-pop click rond 07:05–07:15. Je loopt hierdoor circa 1.5 minuut achter op schema.
* **TC Idle Time:** Je hebt 48.5 seconden totale idle TC time opgelopen, met een piek van 35s rond 04:30 tijdens het luren van je eerste zwijn. Zorg dat je zwijn naar het TC rent vóórdat je schapen op zijn om queue-gaten te voorkomen.
* **Vroege Goudverzameling:** Je stuurde 3 villagers naar goud in Dark Age. Bij een zuivere Scouts rush heb je 0 goud nodig; deze villagers hadden op hout of bessen moeten staan voor eerdere boerderijen.

*Checklist 19-Pop Frank Scouts:*
- 6 op schapen -> 3 op hout (Lumber Camp) -> 1 lure zwijn #1
- 4 op bessen (Mill) -> 1 lure zwijn #2 -> 3 voedsel onder TC -> Loom -> Klik Feudal (~07:10)

## Feudal Age
* **Boerderij Productie (Food Engine):** Je bouwde je eerste boerderij pas op 13:40 en had slechts 11 farms in Feudal Age. Om continu villagers te produceren én Knights te betalen in Castle Age, streef je naar minimaal 14–16 actieve farms vóór minuut 16:00.
* **Opening Executie:** Je bouwde 1 Stable en produceerde 4 Scouts. Goede opening, maar door het gebrek aan farms kon je pas op 19:15 naar Castle Age klikken (benchmark: 18:00–18:30).

## Castle Age
* **Compositie & Civ Kracht:** Als Franks is jouw grootste voordeel de +20% HP op cavalerie en gratis Heavy Plow. Je produceerde echter 8 Crossbowmen en 3 Skirmishers en slechts 2 Knights. Zet vol in op 2 Stables Knights om de Frank civ-bonussen optimaal te benutten.
* **Blacksmith Upgrades:** Je hebt Chain Barding Armor en Forging tijdig onderzocht op weg naar Castle Age. Uitstekende timing!
"""

FEW_SHOT_COACHING_EXAMPLE_EN = """
### EXAMPLE OF HIGH-QUALITY COACHING REPORT (EN):

## Dark Age
* **Feudal Click Timing:** You clicked Feudal Age at 08:45 (525s) with 21 villagers. For a standard 19-pop Frank Scouts build, your target click is 07:05–07:15. You are ~1.5 minutes behind competitive benchmarks.
* **TC Idle Time & Boar Panic:** You accumulated 48.5 seconds of total TC idle time, with a 35s gap around 04:30 while luring your first boar. Boars must be shot twice and lured directly under the Town Center while vils finish the current sheep to eliminate idle time.
* **Premature Gold Mining:** You assigned 3 villagers to gold in Dark Age. Pure Scout openings require 0 gold; those gatherers should have been assigned to wood or berries to fund earlier farms.

*Franks 19-Pop Scouts Checklist:*
- 6 on sheep -> 3 on wood -> 1 lures Boar #1
- 4 on berries -> 1 lures Boar #2 -> 3 on food under TC -> Loom -> Click Feudal (~07:10)

## Feudal Age
* **Farm Engine:** Your first farm went down late at 13:40 and you only seeded 11 total farms across Feudal. You need ~14–16 active farms before minute 16:00 to sustain double-stable Knight production in Castle Age.
* **Opening & Strategy:** You produced 4 Scouts from 1 Stable. Good harassment, but the lack of an early farm engine delayed your Castle Age click to 19:15 (target: 18:00–18:30).

## Castle Age
* **Civ Synergy & Composition:** As Franks, your core power spike is +20% HP cavalry. Instead of committing to the Knight line, you transitioned into 8 Crossbows and 3 Skirmishers. Commit to 2-Stable Knights to leverage Frank civilization strengths.
* **Upgrades Timing:** You researched Chain Barding Armor and Forging while aging up to Castle. Excellent upgrade timing!
"""
