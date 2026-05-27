# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**掼蛋AI客户端** — A rule-based AI decision engine for the Chinese card game 掼蛋 (Guandan). This is a client implementation for the NJUPT AI Competition Platform, featuring:
- WebSocket-based multiplayer game communication
- Multiple AI decision engine variants (M1 rule-based, V6 optimized, RL agents)
- Game state tracking and card analysis
- Self-play testing and batch game execution
- Knowledge base integration for game strategy

**Key Tech Stack:**
- Python 3.8+, PyTorch (for RL agents), Gymnasium (RL environments)
- WebSocket communication, YAML configuration
- Multi-branch development strategy (main, m1-dev, v6-dev)

---

## Project Structure

```
guandan_ai_client/
├── src/
│   ├── communication/       # WebSocket clients (yf1_*.py, yf2_*.py for different AI versions)
│   ├── decision/           # Decision engines (stage_router.py, rule_based_decision_engine.py)
│   ├── game_logic/         # Card types, game rules, card tracking, state management
│   ├── knowledge/          # Game knowledge base and retrieval
│   ├── rl_agent/           # Reinforcement learning agent implementations
│   ├── rl_env/             # Gymnasium environment for RL training
│   ├── knowledge_processor/# Knowledge base processing and indexing
│   ├── optimization/       # Performance optimizations and caching
│   ├── tools/              # Utilities (validation, analysis, formatting)
│   ├── data/               # Data collection and replays
│   ├── feedback/           # Training feedback collection
│   └── config_loader.py    # Configuration management
├── batch_executor/         # Batch game testing and execution (GUI + CLI)
├── tests/                  # Unit and integration tests
├── docs/                   # Comprehensive documentation
│   ├── guandan-brain/      # Critical: Issues, iterations, and evaluation logs
│   ├── development/        # Development guides
│   ├── knowledge/          # Game rules and strategies
│   └── training/           # Training reports and analysis
├── config.yaml             # Main configuration file
├── requirements.txt        # Dependencies
└── pytest.ini              # Pytest configuration
```

---

## Critical Rules & Constraints

### 1. Time Handling (MANDATORY)
**All current time references must use system time APIs — NO hardcoded times.**

```python
from datetime import datetime, timedelta

# ✅ CORRECT
current_time = datetime.now()
timestamp = datetime.now().timestamp()
next_check = datetime.now() + timedelta(hours=6)

# ❌ WRONG
fixed_time = "2025-01-01 12:00:00"  # Never hardcode
timestamp = 1704067200              # Never hardcode
```

**Applies to:** log timestamps, schedule calculations, quiet-hours checks, data timestamps.

### 2. JSON Message Format
- Must strictly comply with platform JSON schema (game messages, actions)
- Use `{"actIndex": X}` for action responses
- Validate message structure before processing

### 3. Team Identification
- Players 1 & 3 form one team
- Players 2 & 4 form one team
- Formula: `teammate_pos = (my_pos + 2) % 4`

### 4. Decision Response Time
- Target: < 1 second per decision
- Configured in `config.yaml` as `max_decision_time` (default 0.8s)

### 5. Platform Check Intervals
- Minimum 6 hours between checks
- Quiet hours: 0:00–6:00 (no checks)
- See `src/monitor/fetcher.py` for implementation

---

## Branch Strategy

**Dual-branch parallel development for independent AI training:**

| Branch | Purpose | Entry Points |
|--------|---------|--------------|
| `main` | Stable releases | Primary |
| `m1-dev` | M1 rule-based engine | `src/communication/yf1_m1.py`, `yf2_m1.py` |
| `v6-dev` | V6 optimized variant | `src/communication/yf1_v6.py`, `yf2_v6.py` |

**Always switch branches when testing different versions.**

---

## Common Tasks

### Running the AI Client

**Option 1: Manual two-player test (m1-dev branch)**
```bash
git checkout m1-dev
# Terminal 1
python src/communication/yf1_m1.py
# Terminal 2 (new window)
python src/communication/yf2_m1.py
```

**Option 2: Batch testing with GUI (recommended)**
```bash
git checkout m1-dev
START_M1_GUI.bat  # Windows only; run `python batch_executor_gui_m3.py` on other OS
```

**Option 3: Check platform updates**
```bash
python -c "from src.monitor.fetcher import PlatformInfoFetcher; \
           fetcher = PlatformInfoFetcher(); print(fetcher.check_updates())"
```

### Running Tests

```bash
# All tests
pytest

# Single test file
pytest tests/test_decision_engine.py

# With coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Type checking (if mypy installed)
mypy src/

# Code style (PEP 8)
python -m py_compile src/**/*.py  # Basic syntax check
```

---

## Architecture Patterns

### 1. Decision Engine Hierarchy (M1 Reference)

```python
RuleBasedDecisionEngineM1 (main entry)
├── StageRouter (5-stage routing: opening, mid-early, mid-late, endgame-early, endgame-late)
│   ├── OpeningActiveHandler / OpeningPassiveHandler
│   ├── ... (stage handlers for each phase)
│   └── EndgameLateActiveHandler / EndgameLatePassiveHandler
├── StrategyEngine (teammate protection, priority system, card value system)
└── HandStructureAnalyzer (combo identification, structure optimization)
```

**Key insight:** Active (player initiates) vs. passive (player responds) decisions follow separate code paths.

### 2. State Management

`EnhancedGameStateManager` centralizes game state:
- Tracks hand cards, board position, teammate/opponent status
- Integrates `CardTracker` for card history and remaining deck inference
- Provides query interfaces: `is_passive_play()`, `is_teammate_action()`, etc.

### 3. Card Tracking

`CardTracker` maintains:
- Per-player play history (`player_history[pos]['send']`)
- Remaining deck per suit/rank
- PASS counts for each player

### 4. Multi-Factor Evaluation

`MultiFactorEvaluator` scores actions using weighted factors:
- Remaining cards (0.25)
- Card type value (0.20)
- Cooperation potential (0.20)
- Risk (0.15), Timing (0.10), Hand structure (0.10)

Weights configurable in `config.yaml` under `evaluation.weights`.

---

## Key Files to Know

| File | Purpose |
|------|---------|
| `src/decision/stage_router.py` | Phase-based routing for M1 decisions |
| `src/game_logic/guandan_constants.py` | Card types, ranks, game rules constants |
| `src/communication/game_recorder.py` | Records game replays for analysis |
| `src/knowledge/yaml_integration.py` | Loads game knowledge from YAML files |
| `batch_executor/executor.py` | Runs batch games, tracks victory stats |
| `docs/guandan-brain/` | **READ BEFORE MODIFYING DECISION LOGIC**: issues, iterations, eval logs |

---

## Before Modifying Decision Logic

**MUST READ:** `docs/guandan-brain/README.md` for:
- Open issues and known bugs
- Previous optimization attempts and outcomes
- Evaluation results and performance metrics

This prevents redundant work and ensures alignment with prior experiments.

---

## Key Integration Points

### WebSocket Communication
- Input: `{"type": "act", "stage": "play", "handCards": [...], "actionList": [[...], ...], ...}`
- Output: `{"actIndex": X}` where X is the chosen action index
- See `src/communication/game_recorder.py` for message flow

### Configuration
```yaml
decision:
  max_decision_time: 0.8  # Seconds
  enable_card_tracking: true
cooperation:
  support_threshold: 15   # Min remaining cards to cooperate
```

Load via: `from src.config_loader import get_config; config = get_config()`

### Knowledge Retrieval
```python
from src.knowledge.retriever import KnowledgeRetriever
retriever = KnowledgeRetriever()
strategy = retriever.query("opening", {"hand_rank": 2})  # Query strategies
```

---

## Testing Strategy

### Unit Tests
Test individual modules in isolation (e.g., CardTracker, HandCombiner):
```bash
pytest tests/test_card_tracking.py -v
```

### Integration Tests
Test decision engine end-to-end with mock game states:
```bash
pytest tests/test_decision_engine.py -v
```

### Batch Testing
Run multi-game tournaments to measure win rate:
```bash
python batch_executor/executor.py --games 100 --log_results
```

---

## Performance Considerations

1. **Decision Timeout:** Monitor `decision_timer` to ensure < 0.8s per turn
2. **Card Tracking:** O(1) lookups via `CardTracker.get_remaining_cards(suit, rank)`
3. **Memory:** Game state resets per round (small footprint)
4. **Caching:** `OptimizationCache` layer available for repeated computations

---

## Deployment Checklist

Before pushing to main:
- ✅ All tests pass: `pytest`
- ✅ No hardcoded times (grep for `"202[0-9]-` to detect fixed dates)
- ✅ Decision time < 1s on average
- ✅ JSON message format validated
- ✅ Read `docs/guandan-brain/EVAL.md` for context on changes

---

## Helpful References

- **Platform Guide:** https://gameai.njupt.edu.cn/gameaicompetition/gameGD/index.html
- **Game Rules:** `docs/knowledge/rules/` (Chinese official rules with local variations)
- **Strategy Docs:** `docs/knowledge/strategy/` (opening, mid-game, endgame tactics)
- **Agentic Patterns:** https://adp.xindoo.xyz/ (routing, planning, multi-agent patterns referenced in M1)

---

## Git Workflow

```bash
# Pull latest before starting
git checkout m1-dev
git pull origin m1-dev

# Create feature branch
git checkout -b feature/my-feature

# Commit with descriptive message
git commit -m "feat: add X to Y decision logic"

# Push and create PR
git push origin feature/my-feature
```

**Note:** Always verify branch before testing (test M1 on `m1-dev`, V6 on `v6-dev`).

---

## Debugging Tips

- **Check card tracking:** `python -c "from src.game_logic.card_tracking import CardTracker; ct = CardTracker(); print(ct.remaining_cards)"`
- **Inspect game state:** Enable `DEBUG=1` in `.env` for verbose logging
- **Replay analysis:** Use `src/communication/game_recorder.py` to extract decision traces
- **Performance profiling:** Use `cProfile` on `decision_engine.decide()` to find bottlenecks

---

**Last Updated:** 2026-05-27  
**Version:** 1.0  
**Platform Version:** v1006
