# Pilot run 20261101-2336_1xgeforce-rtx-3060_qwen3-8b-awq_s0

- **Status:** completed, 2 of 2 rounds complete
- **Model:** Qwen/Qwen3-8B-AWQ, seed 0
- **GPUs:** 1 × NVIDIA GeForce RTX 3060, 12 GiB in total
- **Total time:** 0.52 h; model load 74.0 s
- **Raw output size:** 7 MB for this run

## Cost by phase

| Phase | Total | s/round | gen tok/s | gen tokens/call | Hit max_tokens | Preemptions |
| --- | --- | --- | --- | --- | --- | --- |
| Policy | 0.11 h | 204.8 | 488 | 999 | 99.0% | 300 |
| Judge | 0.38 h | 679.7 | 592 | 1005 | 94.2% | 3299 |

CPU work between rounds (answer checks, saving): 0.00 h in total, 0.0–0.0 s/round.

## Growth over rounds

| Round | Policy s | Judge s | Largest prompt (tokens) | KV cache peak | Peak RSS (GiB) |
| --- | --- | --- | --- | --- | --- |
| 0 | 180.5 | 685.5 | 1025 | 1.00 | 1.1 |
| 1 | 229.1 | 674.0 | 1152 | 1.00 | 1.13 |

## GPU during the run

| GPU | Samples | Mean util % | Peak memory (GiB) | Max power (W) | Max temp (°C) | Throttle codes |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0 | 182 | 95 | 11.7 / 12 | 170.2 | 69.0 | 0x0000000000000000 ×116, 0x0000000000000004 ×61, 0x0000000000000001 ×5 |

## Estimated hours for one 51-round run

**Estimates, not measurements**, for 100 problems on this machine. Rounds not reached are extrapolated with a straight line, which cannot foresee a slowdown from a full KV cache. Short-history rows reuse the early rounds of this run.

| Run type | Hours |
| --- | --- |
| k = 3, self-judge | 12.88 |
| k = 0, self-judge | 12.53 |
| k = 0, no judge calls (Best-of-N) | 2.90 |

## Success (setup check)

Authors' rule (`plots.ipynb`): `accuracy_reward == 0`. Strict: also `format_reward == 0`, so the answer must use the four given numbers. Their plots also skip round 0. One seed: not a result.

| Round | Authors' rule | So far | Strict | So far | Format failures | No answer tag |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 2 | 2 | 1 | 1 | 64 | 54 |
| 1 | 3 | 5 | 3 | 4 | 80 | 75 |
