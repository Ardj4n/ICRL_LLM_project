# Authors' code

From 2026-11-01.

- Pinned to `43429cd` (tag `icrl-proposal-base`), synced by `tools/sync_authors.py` from a clone in `ignored/`. 7 API keys removed. `ignored/` still holds them.
- Its Game of 24 code is identical to `6fd3963`, which added vLLM.
- All 4 upstream branches checked: none is a better base.
- Paper's exact commit unknown. It reports Game of 24 on GPT-4.1 only, so there is no published Qwen3 number; nearest commits are `b85f663`-`1d20fdb`.
- For the report: *"We use the authors' code at commit `43429cd` with their vLLM path. The paper reports Game of 24 only on GPT-4.1 and states no commit."*

```bash
python tools/sync_authors.py --dry-run
python tools/sync_authors.py [--tag other-tag] [--force]
```

## Issues

- Success in `plots.ipynb` is `accuracy_reward == 0` only, on rounds 1-49: wrong numbers can count as solved. `summarize.py` reports this and a strict rule.
- Requirements do not install as written: see `pilot/requirements-overrides.txt`.
- No seed set: real runs must pass one.
- `load_samples` restarts from round 0: no real resume.
