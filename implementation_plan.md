# Implementation Plan - Self-Learning Guandan AI (V5)

## Goal Description
Transition the Guandan AI from a mechanical Rule-Based System (V4) to a **Self-Learning Reinforcement Learning (RL) System (V5)**. The new AI will learn strategies autonomously through self-play, similar to how humans learn: starting with basic rules, gaining experience through matches, and refining strategies by studying "textbooks" (strategy guides) and "replays" (expert games).

## User Review Required
> [!IMPORTANT]
> **Paradigm Shift**: We are moving from "coding logic" to "training models". The quality of the AI will depend on *training time* and *data quality* rather than just code correctness.
> **Resource Intensive**: Training requires significant CPU/GPU time.
> **New Dependencies**: `torch`, `gymnasium`, `numpy`.

## Proposed Architecture

### 1. The Playground (Environment Layer)
A high-speed, local simulation of the Guandan game to allow millions of training steps.

#### [NEW] `src/rl_env/`
- **`game_engine.py`**: A pure-logic, high-performance game state machine.
    - *Features*: State management, rule validation, winner determination.
    - *Optimization*: Must be much faster than the current `game_logic` used for the websocket client.
- **`guandan_env.py`**: A `gymnasium.Env` wrapper.
    - `step(action)`: Returns `(observation, reward, terminated, truncated, info)`.
    - `reward_function`: A crucial component that combines:
        - **Game Result**: +100 for win, -100 for loss.
        - **Strategy Shaping**: Small rewards for following "good practices" (defined by the Knowledge Module).

### 2. The Brain (Agent Layer)
A neural network that perceives the game state and decides on actions.

#### [NEW] `src/rl_agent/`
- **`model.py`**: The Neural Network Architecture.
    - *Input*: Matrix representation of Hand Cards, Table Cards, History, and Teammate Status.
    - *Output*: Probability distribution over legal actions.
- **`agent.py`**: The RL Algorithm (e.g., PPO - Proximal Policy Optimization).
    - Supports `act()` for inference and `learn()` for training.

### 3. The Teacher (Knowledge Integration Layer)
This is the key differentiator. It allows the AI to learn from human knowledge, not just random trial-and-error.

#### [NEW] `src/knowledge_processor/`
- **`replay_parser.py`**: Converts human game logs (`.json`) into training datasets for **Behavior Cloning (BC)**. This gives the AI a "head start" by imitating experts.
- **`strategy_encoder.py`**: Translates text-based rules (e.g., "Keep a straight flush for the end") into **Reward Shaping Functions**.
    - *Example*: If the AI plays a Straight Flush early when it could have won later, it receives a small penalty, guiding it towards the text-based strategy.

### 4. The Critic (Self-Reflection Layer)
Mimics a human reviewing their own game after a match.

#### [NEW] `src/analysis/`
- **`battle_analyst.py`**: Runs after every training episode.
    - Checks for "Blunders" (moves that drastically reduced win probability).
    - Updates a "Mistake Database" to prioritize training on those specific scenarios.

### 5. The Dojo (Training Layer)
The loop where learning happens.

#### [NEW] `src/train/`
- **`pretrain.py`**: Supervised learning phase using `replay_parser` data (Imitating Humans).
- **`self_play.py`**: RL phase where the AI plays against itself (or previous versions of itself).
- **`curriculum.py`**: Manages difficulty. Starts with "Simple Rules", then "Complex Strategies".

## Implementation Steps

### Phase 1: Foundation (The Playground)
- [ ] Implement `game_engine.py` (Fast Logic).
- [ ] Implement `guandan_env.py` (Gym Interface).
- [ ] Verify with random agents.

### Phase 2: Imitation (The Student)
- [ ] Implement `replay_parser.py` to ingest existing game logs.
- [ ] Build `model.py` (Neural Net).
- [ ] Run `pretrain.py` to clone behavior from V4/Human logs.

### Phase 3: Evolution (The Fighter)
- [ ] Implement `agent.py` (PPO/DQN).
- [ ] Run `self_play.py` to improve beyond the imitation baseline.
- [ ] Integrate `strategy_encoder.py` to reward "smart" plays defined in text guides.

### Phase 4: Integration (The Competitor)
- [ ] Create `rl_decision_engine.py` to plug the trained model into the main game client.
- [ ] Deploy to the competition platform.

## Verification Plan

### Automated Tests
- **Logic Correctness**: Ensure `game_engine` perfectly matches official rules.
- **Tensor Shapes**: Verify Neural Network inputs/outputs match the environment.

### Performance Metrics
- **Win Rate**: vs Random Agent (Target: >95%), vs Rule-Based V4 (Target: >55%).
- **Valid Move Rate**: % of times the NN outputs a legal move (Target: 100% via masking).
