# Compute pilot on Renku

Measures whether Renku is enough for the planned runs. It runs the authors' Game of 24 experiment (`authors/experiments/game24/game24_icrl.py`) **unchanged**, on the real 100 problems, and saves small result files to git for the group to evaluate. It does not decide anything.

## Before starting

Note these from the Renku UI, because they cannot be read from inside the session:

- the resource class name
- the pool's quota, or the GPU hours granted
- the auto-pause and deletion timers

**The auto-pause timer matters most.** The public pool pauses a session after 2 hours idle, and each pool can set its own timers. A pause can kill a running process, and deleting a session deletes its disk. Check that a busy GPU counts as "not idle" on our pool.

## Where the model lives

| Location | Pause | Shutdown | Cost |
| --- | --- | --- | --- |
| Session disk | Kept for about two weeks | **Deleted** | Download again after a shutdown |
| Data connector (e.g. S3 bucket) | Kept | Kept | Needs a bucket; loading over a network mount may be slow |
| Git | Kept | Kept | Only for small files: results, not weights or raw outputs |

The weights are public on Hugging Face, so losing them costs only the download time. The results are the part that cannot be recovered, and step 2 and step 5 commit them. Pause sessions rather than shutting them down.

For the pilot, the session disk is enough if it has room: its timings then measure a fast local disk. `HF_HOME` must be set in **every new terminal**, and the scripts stop if it is missing.

```bash
export HF_HOME=/path/on/the/session/disk
```

Use a data connector if the download is too slow to repeat. To avoid the symlinks of the Hugging Face cache on a network mount, download into a plain folder and pass that folder as the model:

```bash
hf download Qwen/Qwen3-32B --local-dir /mount/of/connector/qwen3-32b
$PY pilot/run_game24_pilot.py --model /mount/of/connector/qwen3-32b --rounds 2
```

If `model_load_s` in `run.json` is too high from there, copy the folder to the session disk at the start of each session. The probe measures both options: `network_to_huggingface` for the download speed, and `--disk connector=/mount/of/connector` for the write speed.

## Steps

Run from the repository root, in the terminal of a Renku VS Code session with GPUs. `uv` is already installed there.

**1. Set up** (installs into `pilot/runs/_deps/`, which is lost at shutdown like the rest of the session disk). `HF_HOME` needs about 70 GB free for Qwen3-32B, or 30 GB for Qwen3-14B.

```bash
export HF_HOME=/path/on/a/large/disk
bash pilot/setup_renku.sh
PY=pilot/runs/_deps/venv/bin/python
```

**2. Probe the machine and commit straight away**, so this data is safe whatever happens next. The probe takes about a minute. Use `--disk LABEL=PATH` to test another disk, such as a data connector.

```bash
$PY pilot/probe_system.py --resource-class "..." --idle-timeout "..." --quota-notes "..."
git add pilot/results && git commit -m "Pilot: system probe" && git push
```

**3. Smoke test.** Two rounds, on all visible GPUs. The first time, this also downloads the model. Check that `summary.md` shows token counts and preemptions, not `n/a`.

```bash
$PY pilot/run_game24_pilot.py --rounds 2
$PY pilot/summarize.py pilot/results/<run_id>
```

**4. Pilot.** Run it with `nohup`, so that it survives closing the terminal, with a time limit that fits the session. It stops cleanly at the start of the next round.

```bash
nohup $PY pilot/run_game24_pilot.py --rounds 51 --max-minutes 240 > pilot/runs/pilot.out 2>&1 &
tail -f pilot/runs/pilot.out   # Ctrl+C stops watching, not the run
```

`nohup` does not protect against a session pause. Check whether closing the browser tab counts as idle on our pool.

**5. Summarise and commit.**

```bash
$PY pilot/summarize.py pilot/results/<run_id>
git add pilot/results && git commit -m "Pilot: <model> on <gpu>" && git push
```

If Qwen3-32B does not fit in memory, the run is recorded as `crashed`, with the error. Commit that too, then repeat steps 3–5 with `--model Qwen/Qwen3-14B`, as the proposal plans.

If the session dies, `rounds.jsonl` keeps every finished call and `run.json` stays at `running`. `summarize.py` still works on it.

## What is saved

`pilot/results/<date>_<gpu>_<model>_s<seed>/` goes to git:

| File | Content |
| --- | --- |
| `summary.md` | Read this first: cost by phase, growth, GPU use, estimated hours, success |
| `system.json` | GPUs, CPU and memory with container limits, disks, package versions, git commit |
| `run.json` | Exact command, status, hash of the authors' file, crash error if any |
| `rounds.jsonl` | One line per generate call: seconds, tokens, truncations, preemptions, KV cache |
| `gpu_samples.jsonl` | Utilization, memory, power, temperature and throttling, every 10 s |
| `success_by_round.json` | Problems solved per round and so far |

`pilot/runs/` is ignored by git. It holds the authors' raw outputs, the log and the installed dependencies, and it is lost with the session.

Only allowlisted environment variables are saved, because Renku sessions can hold tokens. Check `system.json` and `run.json` anyway before pushing.

## How to read the results

- **Judge against policy.** Each round makes 100 policy calls and 400 judge calls. At the token limits that is at most 509,600 generated tokens per round. "Hit max_tokens" shows how close we get: the prompts go to vLLM without a chat template, so generations may not stop by themselves.
- **Growth.** Prompts grow every round, so a short run understates the cost of the late ones. Rows marked as estimates use a straight line, which cannot foresee a full KV cache. Rising preemptions or a KV cache peak near 1.0 are the warning sign. Only a run that reaches the last round rules this out.
- **Estimated hours.** These are for one run of each kind. The k = 3, k = 0 and no-judge rows reuse parts of this run and are not measured separately. Multiply by the number of runs in the proposal.

## Known problems in the authors' code

- **Requirements.** Their file cannot be installed as written. `requirements-overrides.txt` lists the three pins we changed and why, and `requirements.lock.txt` is the result.
- **Seeds.** Their code never sets a seed, so it runs with vLLM's default every time. The wrapper passes `--seed`; the real runs must do the same, or "3 seeds" gives three identical runs.
- **No real resume.** `load_samples` reloads the saved state, but the loop still restarts from round 0. If real runs are longer than a session lasts, this must be fixed first.

## Testing without a GPU

```bash
uv run --no-project --python 3.11 --with numpy==1.26.4 --with sympy==1.13.3 \
    python pilot/run_game24_pilot.py --dry-run --rounds 5
```

This uses the fake backend in `fake_backend.py`, runs the authors' real code on top of it, and writes only to `pilot/runs/`.
