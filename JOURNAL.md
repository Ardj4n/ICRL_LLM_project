# Journal

Details and full steps: [pilot/README.md](pilot/README.md).

## To do

- [ ] Commit the uncommitted setup (`tools/`, `authors/`, `pilot/`, `JOURNAL.md`).
- [ ] Get a GPU and enough disk on Renku (current session has neither).
- [ ] Run the pilot and commit `pilot/results/`.
- [ ] Fix `PROPOSAL.md`: Claim 3's "explore"/"exploit" sentence; Claim 2 cites a missing Claim 1.

## Decisions

| # | Decision | Options | Recommendation |
| --- | --- | --- | --- |
| 1 | Model | 32B, 14B, 8B-AWQ | By VRAM: 32B from ~100 GB, 14B from 40 GB, 8B-AWQ on 12 GB |
| 2 | Model good enough? | Keep or change | Must beat Best-of-N in the pilot |
| 3 | Rounds | 30-50 | Fewest that show the trend |
| 4 | More compute? | Renku or more | After the pilot: hours × runs vs quota |
| 5 | Runs in scope | Claim 2 = 21 runs (15 new), plus Claims 1 and 3 | Agree on one final list |
| 6 | Success metric | Authors' or strict | Report both, pick after the pilot |
| 7 | Raw outputs | Session disk or data connector | Connector for real runs |
| 8 | Checkpoint resume | Implement or not | Needed if a run outlasts a session |
| 9 | Changing authors' code | Wrapper or edits | Wrapper: `sync_authors.py` overwrites `authors/` |

## 2026-11-01

**Authors' code**

- Pinned to `43429cd` (tag `icrl-proposal-base`), synced by `tools/sync_authors.py` from a clone in `ignored/`. 7 API keys removed. `ignored/` still holds them.
- Its Game of 24 code is identical to `6fd3963`, which added vLLM.
- All 4 upstream branches checked: none is a better base.
- Paper's exact commit unknown. It reports Game of 24 on GPT-4.1 only, so there is no published Qwen3 number; nearest commits are `b85f663`-`1d20fdb`.
- For the report: *"We use the authors' code at commit `43429cd` with their vLLM path. The paper reports Game of 24 only on GPT-4.1 and states no commit."*

```bash
python tools/sync_authors.py --dry-run
python tools/sync_authors.py [--tag other-tag] [--force]
```

**Authors' code issues**

- Success in `plots.ipynb` is `accuracy_reward == 0` only, on rounds 1-49: wrong numbers can count as solved. `summarize.py` reports this and a strict rule.
- Requirements do not install as written: see `pilot/requirements-overrides.txt`.
- No seed set: real runs must pass one.
- `load_samples` restarts from round 0: no real resume.

**Pilot** (`pilot/`, branch `pilot-compute`)

- Measures system, time, tokens and GPU, with the authors' code unchanged.
- Tested only on a fake backend, not yet on vLLM or Renku.

**First Renku session**

- No GPU. 8 cores, 31 GB RAM.
- `/home/renku/work` has 7.8 GB; `overlay` has 144 GB, persistence unknown.
- Needs a GPU and ~100 GB of disk for 32B, ~50 GB for 14B.
- Session disk survives a pause, not a shutdown.

**Estimates** (to replace with pilot data; assumes ~7000 tokens per request in late rounds)

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

### Pilot commands

In a Renku VS Code terminal with a GPU. Set `HF_HOME` in every new terminal.

```bash
git clone -b pilot-compute https://github.com/Ardj4n/ICRL_LLM_project.git
cd ICRL_LLM_project
export HF_HOME=/path/on/a/large/disk
bash pilot/setup_renku.sh
PY=pilot/runs/_deps/venv/bin/python

$PY pilot/probe_system.py --resource-class "..." --idle-timeout "..." --quota-notes "..."
git add pilot/results && git commit -m "Pilot: system probe" && git push

$PY pilot/run_game24_pilot.py --rounds 2     # smoke test; add --model to change model
$PY pilot/summarize.py pilot/results/<run_id>

nohup $PY pilot/run_game24_pilot.py --rounds 51 --max-minutes 240 > pilot/runs/pilot.out 2>&1 &
tail -f pilot/runs/pilot.out

$PY pilot/summarize.py pilot/results/<run_id>
git add pilot/results && git commit -m "Pilot: <model> on <gpu>" && git push
```

Without a GPU:

```bash
uv run --no-project --python 3.11 --with numpy==1.26.4 --with sympy==1.13.3 \
    python pilot/run_game24_pilot.py --dry-run --rounds 5
```

## 2026-10-27

- TA feedback: deep over broad; Claim 2 on track, Claim 3 interesting; discuss control and experimental variables.
- Claim 3 rewritten in `README.md` (uncommitted): Game of 24 only, label × true/shuffled scores, frozen-context probe.
- `PROPOSAL.md` added (`19a6b27`).

## 2026-10-21

- Repository set up; authors' code moved to `authors/` (`5058e3c`, `d6123d4`, `80e001a`).
