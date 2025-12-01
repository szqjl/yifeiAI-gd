# Go Online: Expansion Plan for Guandan AI

## Objective
Expand the Self-Learning Guandan AI (V5) from a local training environment to a competitive online agent capable of playing against other AIs and humans on various platforms.

## 1. Protocol Adaptation Layer (PAL)
Currently, the client (`yf1_v4.py`) is hardcoded for the NJUPT competition platform. To play elsewhere, we need a flexible communication layer.

### Proposed Changes
*   **`src/communication/adapter.py`**: Create an abstract base class `GameAdapter`.
    *   `connect(url, token)`
    *   `send_action(action)`
    *   `receive_message()` -> Standardized `GameState` object.
*   **Implementations**:
    *   `NJUPTAdapter`: Existing logic.
    *   `TencentAdapter`: (Hypothetical) For Tencent games.
    *   `BrowserAdapter`: Uses Selenium/Puppeteer to play on web-based platforms without APIs.

## 2. Human-Like Behavior (Turing Test)
When playing against humans, mechanical instant responses are a giveaway and can be annoying or flagged as botting.

### Proposed Changes
*   **`src/decision/behavior_modulator.py`**:
    *   **Reaction Time**: Add variable delays based on move complexity. (e.g., Single card = fast, complex strategy = slow).
    *   **Mistake Simulation**: Occasionally make "human" errors in low-stakes situations if the win rate is too high (to mask identity).
    *   **Chat/Emotes**: Basic interaction capabilities (e.g., "Good game", "Nice hand").

## 3. Online Learning Pipeline (Continuous Improvement)
The "Dojo" should not stop at local self-play. Real-world matches provide the best data.

### Proposed Changes
*   **Cloud Sync**:
    *   `src/data/cloud_sync.py`: Automatically upload `game_records/*.json` to a central S3 bucket or server after each match.
*   **Active Learning**:
    *   The training server downloads these new logs.
    *   `replay_parser.py` extracts "Novel Situations" (states not seen in self-play).
    *   The model is retrained on these edge cases and pushed back to the client.

## 4. Deployment & Scalability
To play many matches simultaneously (e.g., ranking up multiple accounts).

### Proposed Changes
*   **Dockerization**:
    *   Create `Dockerfile` to package the Environment + Agent + Client.
*   **Orchestrator**:
    *   Use `docker-compose` or Kubernetes to run 10-100 agents in parallel.
    *   **Central Config**: A dashboard to monitor win rates and update `config.yaml` dynamically.

## Roadmap

### Phase 1: Abstraction
- [ ] Refactor `yf1_v4.py` to use `GameAdapter`.
- [ ] Standardize the `GameState` internal format.

### Phase 2: Humanization
- [ ] Implement `behavior_modulator.py`.
- [ ] Add random delay logic to `RLDecisionEngine`.

### Phase 3: The Cloud
- [ ] Set up a log server.
- [ ] Implement auto-upload of replays.

### Phase 4: Conquest
- [ ] Deploy to public platforms.
- [ ] Analyze performance vs Humans vs Other AIs.
