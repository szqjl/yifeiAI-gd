# Deploying FableDan to Botzone

[Botzone](https://www.botzone.org.cn/) hosts a rated GuanDan ladder. This guide
covers packaging and uploading a trained FableDan model as a bot.

## 1. Package the submission zip

The bot is pure Python + NumPy (which Botzone's `python3` environment provides),
so no PyTorch is needed at deploy time. From the repository root:

```bash
# Option A — embed the weights in the zip (simplest; use if within the size limit)
python botzone/pack_bot.py --weights ckpts/run1/best.npz --embed-weights
# -> dist/fabledan_bot.zip

# Option B — keep weights separate (if the zip would exceed the source-size limit)
python botzone/pack_bot.py --weights ckpts/run1/best.npz
# -> dist/fabledan_bot.zip       (code only)
# -> dist/fabledan_weights.npz   (upload to your Botzone user storage space)
```

Both zips contain `__main__.py` (the bot entry) plus the pure-Python `fabledan/`
modules. During GPU training, `train_fast` also auto-produces
`dist/fabledan_bot_ready.zip` (weights embedded) every time evaluation improves.

## 2. Create the bot

1. Sign in at <https://www.botzone.org.cn> and open **My Bots**.
2. Click **Create a new Bot** and fill in the form:
   - **Name**: e.g. `FableDan`
   - **Game**: **GuanDan**
   - **Source code**: upload `dist/fabledan_bot.zip`
   - **Compiler / language**: **python3** (the highest python3 version in the
     list). A `.zip` whose root contains `__main__.py` is Botzone's multi-file
     Python upload format.
   - Leave **"simple interaction" unchecked** — this bot uses the JSON protocol.
3. Submit. Botzone runs a quick syntax check; the bot then becomes available.

## 3. Verify it plays correctly

1. On the bot page, start a test match on GuanDan — you can fill all four seats
   with FableDan (self-play).
2. Open the replay:
   - A complete play-by-play means the protocol is correct.
   - In the first-turn response's `debug` field, look for `model=transformer`
     (trained model) or `model=mlp` (demo weights). `model=rule` means the
     weights were not loaded — see troubleshooting below.
3. When it works, enable it on the ladder (the GuanDan ranked queue schedules
   rated matches automatically).

## 4. Update to a new version

In **My Bots**, open FableDan → **Upload new version**, choose the latest
`dist/fabledan_bot_ready.zip`, keep the compiler on **python3**. The ladder
keeps the bot's history and score; no need to recreate it.

## 5. Runtime environment

- Single-core CPU, 256 MB memory cap.
- Per-turn time limit with a python multiplier; the first turn is relaxed.
- `python3` ships NumPy (this bot's only dependency); no PyTorch.
- Long-running mode is enabled, so weights load once on the first turn.
- Measured inference: ~20–40 ms per decision, weight load < 1 s.

## 6. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Compile failure | Make sure the compiler is **python3**, not python2 / C++ |
| First-turn timeout | Zip too large or slow weight load — use the separate-weights option |
| `debug` shows `model=rule` | Weights not found: for the embedded option, confirm `fabledan_weights.npz` is at the zip root; for the storage option, confirm the file name and that the bot reads it from `data/` |
| Illegal-move loss | Capture the match log (full request/response) so it can be reproduced and fixed |
| Zip exceeds source-size limit | Use the separate-weights option and upload `dist/fabledan_weights.npz` to your Botzone user storage space; the bot reads `data/fabledan_weights.npz` automatically |
