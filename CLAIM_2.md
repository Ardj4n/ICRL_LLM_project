# Claim 2: what this machine covers and what Renku needs

As of 2026-11-03. The aspects come from [PROPOSAL.md](PROPOSAL.md).

"This machine" is an RTX 3060 with 12 GB (10.96 GiB free in WSL2), running Qwen3-8B-AWQ with the chat template. Its costs are projections from one 3-round run with one seed, so only a long run can confirm them.

## In short

- **This machine** can run every condition, but only on 8B-AWQ, not on the proposal's model. All 21 runs at 30 rounds take about 74 h of GPU. A reduced set of 12 runs takes about 31 h.
- **Renku** currently has no GPU. To reach the proposal it needs about 96 GB of VRAM for 32B, or about 48 GB for the 14B fallback, plus about 100 GB or 50 GB of lasting disk.
- **Unknown on both:** whether ICRL beats Best-of-N. If it does not, there is nothing to ablate.

## Coverage by aspect

"Full" means the aspect can run here on 8B-AWQ, not on 32B.

| Aspect | Desired | This machine | Covered | Renku needs |
| --- | --- | --- | --- | --- |
| Model | 32B, bf16, thinking off, as policy and judge | 8B-AWQ: a quarter of the parameters, quantized | None | From 68 GB of VRAM, about 96 GB in practice |
| Fallback | 14B, same setup | Does not fit: even 14B-AWQ needs about 13 GB | None | From 32 GB of VRAM, about 48 GB in practice |
| Generalization | An open model instead of GPT-4.1 | 8B-AWQ is open, but this is a weaker claim than 32B | Part | Check that its model also needs the chat template |
| Reference | Full history, rewards, attempts in order, alternating | Runs, measured for 3 rounds only | Full | The same run on its model |
| k = 3 | Last 3 attempts | Authors' `num_weak_demo`; wrapper option missing | Full, after code | Nothing more |
| k = 0 | No history | `num_weak_demo = 0` fails: `[-0:]` returns the whole history. `--method best-of-n` works | Full | Nothing more |
| Rewards removed | No rewards at all in the prompt | Authors' `no_reward`, but the instructions still mention rewards | Full, after a decision | Nothing more |
| Random or sorted order | Attempts shuffled, or sorted by reward | Not in the authors' code | Full, after code | Nothing more |
| Epsilon-greedy | More exploring with few attempts, less later | Not in the authors' code | Full, after code | Nothing more |
| Success metrics | Per-round and running max | `summarize.py` and `judge_quality.py` | Full | Nothing more |
| Token use | For the context-size conditions | Recorded per call in `rounds.jsonl` | Full | Nothing more |
| 3 seeds, mean and SE | Same problems and rounds | `--seed` exists, only seed 0 used so far; no script for mean and SE yet | Most | Nothing more |
| Test instances | Problems 900-999 | Already used | Full | Nothing more |
| Rounds | Fixed after the pilot | 30 rounds are realistic here, 51 are slow | Most | Hours below |
| Budget | 7 conditions × 3 seeds = 21 runs | About 74 h at 30 rounds | Full, slow | Hours below |

## Cost on this machine

Hours per run. Rewards removed and k = 0 do not need the judge, because the policy never sees its scores. This needs a wrapper option for rewards removed; `--method best-of-n` already does it for k = 0.

| Condition | Runs | 15 rounds | 30 rounds | 51 rounds |
| --- | --- | --- | --- | --- |
| Reference | 3 | 1.8 | 4.8 | 11.0 |
| Random order | 3 | 1.8 | 4.8 | 11.0 |
| Sorted order | 3 | 1.8 | 4.8 | 11.0 |
| Epsilon-greedy | 3 | 1.8 | 4.8 | 11.0 |
| k = 3 | 3 | 1.4 | 2.8 | 4.8 |
| Rewards removed, no judge | 3 | 0.6 | 2.4 | 6.9 |
| k = 0, no judge | 3 | 0.1 | 0.2 | 0.3 |
| **All 21 runs, total** | 21 | **28 h** | **74 h** | **168 h** |
| **Reduced set, total** (reference, k = 3, k = 0, rewards removed) | 12 | **12 h** | **31 h** | **69 h** |

Limits of these numbers:

- Policy time is a straight line through 3 points (12, 36, 50 s).
- Prompts reach about 8,150 tokens at round 50, when the cache holds only about 3 at a time. Late rounds may be slower than the line says.
- The PC must stay on, and there is no real resume: a crash restarts the run from round 0.

## What Renku needs

**GPU.** Requests that fit in the cache at once, at round 29 / round 50. This machine manages about 5 / 3. "No" means one long request does not fit.

| VRAM | 32B | 32B-AWQ | 14B | 14B-AWQ |
| --- | --- | --- | --- | --- |
| 24 GB | no | 3 / 2 | no | 15 / 10 |
| 32 GB | no | 8 / 5 | 2 / 1 | 24 / 16 |
| 40 GB | no | 14 / 9 | 11 / 7 | 34 / 22 |
| 48 GB | no | 20 / 13 | 21 / 13 | 43 / 28 |
| 80 GB | 10 / 7 | 44 / 28 | 58 / 37 | 81 / 52 |
| 96 GB (2 × 48) | 21 / 14 | 54 / 35 | 75 / 48 | 98 / 63 |
| 160 GB (2 × 80) | 68 / 44 | 100 / 65 | 100 / 97 | 100 / 100 |

- "In practice" above means at least 10 requests at round 50. This is my threshold, not a measured one.
- The rule is weights + 1.5 GiB + cache, at 95% of VRAM. The cache cost matched vLLM on 8B-AWQ, but the 1.5 GiB was measured once and may grow with the model.
- The table says what fits, not how fast it runs.
- 32B-AWQ is a possible compromise: same model size, much less VRAM, but not what the proposal says.

**GPU hours.** All 21 runs generate about 83 M tokens at 30 rounds and 140 M at 51, if 32B writes as much as 8B-AWQ. That is not measured. Speed here counts generated tokens per second over a whole run, including prompts and queueing. With 2 GPUs, the quota in GPU hours doubles.

| Speed | 30 rounds | 51 rounds |
| --- | --- | --- |
| This machine (about 310 and 230 tokens/s) | 74 h | 168 h |
| 1000 tokens/s | 23 h | 39 h |
| 2000 tokens/s | 12 h | 20 h |
| 5000 tokens/s | 5 h | 8 h |

**The rest:**

| Need | Now | Required |
| --- | --- | --- |
| GPU | None in the first session | See above |
| Disk | `/home/renku/work` has 7.8 GB; `overlay` has 144 GB, persistence unknown | About 100 GB for 32B or 50 GB for 14B, kept across sessions |
| Outputs | – | Under 5 GB for all runs (estimate), committed or on a data connector |
| Session length | Public pool pauses after 2 h idle; our pool's timers unknown | Longer than one run, or a real resume (Decision 8) |
| Download | Speed unknown | 66 GB for 32B: 1.5-7 h at this machine's 12-2.5 MB/s |

**First step on Renku:** the system probe, then 3 rounds with `--prompt-format chat`. That gives the real speed, replaces the tables above, and shows whether 32B has the same judge problem as 8B-AWQ.

## Needed on both machines

1. **ICRL against Best-of-N.** Solved per round so far: 3, 7, 5, which shows no trend. 15 rounds of ICRL take about 1.8 h and Best-of-N about 6 minutes.
2. **Code**, all in the prompt loop of `game24_icrl.py` and in the wrapper:
   - an option for k (`num_weak_demo`);
   - rewards removed, with the judge cut;
   - random and sorted order (line 165);
   - epsilon-greedy (lines 205-209);
   - a script for mean and SE over seeds.
3. **A check that seeds differ**: only seed 0 has run so far.
4. **Decisions**, since each condition must change one thing only:
   - k = 0: `rejection_sampling` also drops the instructions, so it changes more than the history.
   - Rewards removed: both instructions still talk about rewards.
   - Random order: shuffle once or every round. Sorted order: which direction.
   - Epsilon-greedy: which schedule.
5. **The proposal.**
   - It names 32B or 14B, so using 8B-AWQ must be changed and agreed with the TA, along with the chat template and quantization.
   - Its "15 new runs" assume Claim 1 runs too. Without Claim 1, all 21 are new.

Background: [what is valid](journal/2026-11-03_validity.md), [models](journal/2026-11-03_models.md), [Renku](journal/2026-11-01_renku.md), [decisions](journal/2026-11-03_decisions.md).
