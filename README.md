# Age of Empires Vibe Project
### AI-Powered Replay-to-Coach Telemetry Pipeline (AoE2:DE)

> ⚠️ **DISCLAIMER / RECRUITER NOTICE:**  
> **This is an experimental, "vibe-coded" side project created purely for fun, gaming enjoyment, and LLM experimentation.**  
> It was developed through iterative AI-assisted pair-programming and prompt-driven "vibe coding" sessions rather than being coded entirely by hand from scratch. This notice is intentionally provided for complete professional transparency, so prospective employers, recruiters, and engineering teams can clearly distinguish between my handcrafted production portfolio projects and my exploratory AI sandbox side projects.

---

## 🎯 About The Project

**Age of Empires Vibe Project** is a modular Python CLI application that transforms Age of Empires II: Definitive Edition (`.aoe2record`) binary match replays into deep gameplay telemetry and sharp, human-like AI coaching advice.

Key features:
1. **Binary Replay Telemetry Extraction:** Decodes `.aoe2record` action streams with custom monkeypatches for AoE2:DE Patch 101.103+ (save versions 67.x / 68.x).
2. **Deterministic Heuristic Engine:**
   - **Dark Age:** Millisecond-accurate Feudal click times, Town Center idle gaps cross-referenced with boar lures, Loom timing detection, resource gather distributions.
   - **Feudal Age:** Opening strategy classification (Scouts, Archers, Men-at-Arms, Fast Castle), early gold mining flags, farm build rates (farms/min), Town Center rally point Euclidean distance tracking.
   - **Castle & Imperial Age:** Composition focus score ($0.0 - 1.0$), production scaling counts (Stables, Ranges, TCs, Castles), Blacksmith upgrade timelines.
3. **Core Performance Benchmarks (%):**
   - **Town Center Uptime (%):** Precise active production vs. idle time (CaptureAge equivalent benchmark).
   - **Economy Efficiency Score (%):** Weighted analysis of TC continuity, farm engine pace, and drop-off walking penalties.
   - **Military Value & Focus (%):** Unit line commitment vs. scattered production and Blacksmith armor scaling.
4. **All 45 Civilizations Database:** Complete JSON database (`data/civilizations.json`) of all 45 AoE2:DE civilizations with bonuses, unique units, unique technologies, and strict negative tech-tree constraints (preventing LLM hallucinations like Bulgarian Paladins).
5. **Contextual Matchup AI Coach:** Feeds complete opponent rosters and civ traits to Google Gemini (`gemini-3.5-flash`) to generate structured, constructive coaching in Dutch or English.

---

## 🏗️ Architecture & Structure

```
AgeOfEmpires-Coach/
├── config/
│   └── settings.py           # Environment variables, AoE2 timing & benchmark constants
├── data/
│   ├── models.py             # Strict Pydantic v2 schemas for all telemetry & reports
│   ├── exceptions.py         # Custom domain exceptions (ReplayLoadError, etc.)
│   ├── civ_database.py       # Civ database loader, matchup overview generator
│   └── civilizations.json   # All 45 AoE2:DE civilizations, bonuses & tech limits
├── parser/
│   ├── replay_loader.py      # Binary stream loader & path validation
│   ├── mgz_patch.py          # Compatibility patches for AoE2:DE save versions 67.x/68.x
│   └── mgz_adapter.py        # mgz wrapper isolating third-party binary structs
├── analyzer/
│   ├── age_segmenter.py      # Chronological slicing into Dark, Feudal, Castle, Imperial
│   ├── economy_heuristics.py # Idle TC estimator, boar panic detection, farm build rate
│   ├── military_heuristics.py# Opening detection, composition focus, blacksmith tech
│   ├── spatial_heuristics.py # Euclidean distance micro checks (lure distance, shift-click guards)
│   └── performance_scorer.py # Match performance benchmarks (TC Uptime %, Eco Score %, Military Score %)
├── exporter/
│   └── readable_exporter.py  # JSON export, readable Markdown timeline & coaching export
├── ai/
│   ├── knowledge_base.py     # Civ playbooks, build orders, tactical adaptation rules
│   ├── prompt_builder.py     # Rigorous System Prompt (zero hallucination, matchup context)
│   └── coach_client.py       # Gemini API client with exponential backoff & size guards
├── tests/
│   └── test_core.py          # Comprehensive pytest suite (40 unit tests)
├── run.bat                   # 1-click Dutch Windows launcher with drag-and-drop
├── run_en.bat                # 1-click English Windows launcher with drag-and-drop
├── main.py                   # Typer CLI entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Complete git ignore rules (secrets, venv, replays ignored)
└── README.md
```

---

## 🚀 Quick Start & Usage

### 1. Fastest Way: One-Click Launchers (Windows)
- **Dutch:** Double-click `run.bat` or drag and drop your `.aoe2record` file directly onto `run.bat`.
- **English:** Double-click `run_en.bat` or drag and drop your `.aoe2record` file directly onto `run_en.bat`.

> **Tip:** You can edit `run.bat` or `run_en.bat` and set `set PLAYER_NAME=YourInGameName` to automatically pick your player every time!

### 2. Manual CLI Setup
1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd "AgeOfEmpires-Coach"
   ```

2. **Create virtual environment & install requirements:**
   ```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Configure API Key (for AI coaching):**
   Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
   Add your Google Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-3.5-flash
   ```

4. **Run the Coach:**
   ```bash
   # Run full AI coach (English):
   python main.py coach "path/to/replay.aoe2record" --lang en

   # Run full AI coach (Dutch):
   python main.py coach "path/to/replay.aoe2record" --lang nl

   # Run offline parser only (Zero API cost, exports JSON + Markdown):
   python main.py convert "path/to/replay.aoe2record"
   ```

---

## 🧪 Running Tests

The test suite covers guard clauses, spatial heuristics, boar lure mechanics, shift-click sheep protections, age segmentation, civ database integrity, and performance scoring:

```bash
.\venv\Scripts\pytest.exe
```

```text
============================= 40 passed in 0.27s ==============================
```

---

## 📜 License
MIT License. Created as an experimental vibe project for Age of Empires II enthusiasts.
