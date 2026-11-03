# Estimates

From 2026-11-01. To replace with pilot data; assumes ~7000 tokens per request in late rounds.

Requests in parallel, out of 100, in late rounds:

| VRAM | 32B (65.5 GB) | 14B (29.5 GB) | 8B (16.4 GB) | 8B-AWQ (6.1 GB) |
| --- | --- | --- | --- | --- |
| 12 GB | no | no | no | ~6 |
| 24 GB | no | no | ~6 | – |
| 40 GB | no | ~7 | ~21 | – |
| 48 GB (2×24) | no | ~14 | ~28 | – |
| 80 GB | ~5 | ~40 | ~58 | – |
| 160 GB (2×80) | ~47 | 100 | 100 | – |

Time at the 26M-token worst case of a 51-round run (example speeds):

| Tokens/s | One run | 21 runs |
| --- | --- | --- |
| 5000 | ~1.4 h | ~30 h |
| 1000 | ~7 h | ~150 h |
