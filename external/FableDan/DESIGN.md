# FableDan Design & Roadmap

The baseline recipe FableDan builds on is the one popularized by DanLM:
**raw-history tokenization + a tiny causal Transformer + DMC self-play + a
next-token-prediction (NTP) auxiliary task**, scaled up with a lot of compute.
The algorithm itself is simple; the wins come from the representation and the
sheer volume of self-play experience.

To push further, there are two complementary levers: **stronger learning signal
during training** and **stronger decision-making at deploy time**. The items
below are ordered roughly by priority. ✅ = implemented and on by default,
🔧 = scaffolded in the code, implement as guided.

## ✅ 1. Belief auxiliary head (opponent-hand prediction)

GuanDan is an imperfect-information game; the ceiling on decision quality is set
by how well you infer the hidden information (the three other hands). NTP only
learns card-tracking indirectly. FableDan adds an **oracle-supervised belief
head**: during training the engine knows every hand, so the per-player rank-count
vectors of the three other seats (next / partner / previous, 15 dims each) are a
free label that the context vector regresses against (`--belief-weight 0.05`).
This forces the Transformer to learn precise card counting and inference — a
light-weight version of Suphx oracle-guiding and PerfectDou
perfect-information distillation. The head is dropped at inference (zero cost).

- Implementation: `ring.py::_belief_label` (labels), `model_torch.py::belief_head`,
  `train_fast.py --belief-weight`.
- Expected gain: better mid/late-game decisions on when to beat or pass — exactly
  where card-counting human experts have the edge.

## ✅ 2. Deeper encoder + validated components

Default 4 blocks (vs a typical 3), RoPE + QK-Norm + SwiGLU, NTP (weight 0.02),
top-k ε-greedy, and full coverage of random level / tribute scenarios. NumPy
inference is ~20–40 ms per decision, leaving a large margin under the Botzone
per-turn limit — that margin is the budget for any deploy-time search.

## ✅ 3. Frozen-snapshot shadow evaluation (anti-stagnation)

Every N cycles a frozen self-snapshot is taken, and evaluation also reports
win-rate vs that snapshot. Once the rule-baseline win-rate saturates, this is the
only trustworthy progress signal; a long stretch below ~53% means it is time to
change something (larger model, different auxiliary weights).

## 🔧 4. TD-λ mixed targets (lower DMC variance)

DMC regresses on the whole-round return, which is high-variance and gives coarse
credit assignment. Improvement: have actors also record the next decision point's
max-Q, and train against `z' = β·MC + (1-β)·bootstrap` (start β≈0.95). Roughly:
record the bootstrap value of the previous sample in `ring.py::step`, add a column
to the replay buffer, and mix it in the learner.

## 🔧 5. Opponent pool / league (anti-exploitative collapse)

Pure self-play can converge to a cyclic "only knows how to beat itself" policy.
Improvement: the inference server hosts the current weights plus a randomly
sampled older snapshot, routed by seat (our side current, the other side an old
version, and vice versa). A minimal AlphaStar-league variant. Implement in
`train_fast.py::infer_server` (two models) with seat-tagged actor requests.

## 🔧 6. Deploy-time one-step look-ahead search

On Botzone the bot uses only tens of milliseconds per turn, leaving seconds of
headroom. With that budget it can do **belief sampling + one-step look-ahead**:
sample N determinized worlds from the belief head's opponent-hand distribution,
roll the top-k Q candidates forward one step (opponents respond with the same
model), average, and re-rank. Equivalent to a shallow ISMCTS; biggest payoff on
the pivotal decisions (bomb timing, when to pass). Implement in
`botzone/bot_fabledan.py`, keeping ~0.5 s of safety margin.

## 🔧 7. Scaling and distillation

The last resort once gains flatten: grow `d_model` (128→192) and depth, keep
training the larger model, and — if it ever exceeds the time limit at deploy —
distill back into a small model (the NumPy weights are fp32; int8 quantization
is an option, as DanZero does with int8 ONNX).

## Suggested execution order (long-run plan)

1. Day 1: get `train_fast` running with defaults (belief on); upload the first
   version once rule win-rate ≥ 95%.
2. Days 2–4: keep training, swap the ladder version every 1–2 days; watch the
   vs-snapshot number.
3. From day ~4: implement #6 deploy-time search (bot-side only, no training
   interruption) and A/B it as a separate upload.
4. When vs-snapshot flattens: try #4 TD-λ or #5 opponent pool, one controlled
   experiment at a time.
5. When everything flattens: scale the model up (#7) and continue.

## Honest expectations

Architecture amplifies the value of each sample, but the hard currency of RL is
still compute × time. A few GPU-days to reach DanLM-scale experience, plus the
improvements above, gives a real shot at being competitive — but the leaderboard
moves too. Treat it as ongoing operation, not a one-shot.
