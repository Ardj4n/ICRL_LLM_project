"""Run the authors' Game of 24 experiment unchanged and measure what it costs.

authors/experiments/game24/game24_icrl.py is imported as it is. Before the
import, vllm.LLM is replaced by a wrapper that overrides the hard-coded model,
GPU count and seed, and times every generate call. After the import, the module's
`open` and `os` are replaced so that its hard-coded output path lands in pilot/runs/.

Measurements are flushed after every call, so they survive a killed session.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import json
import builtins
import os
import subprocess
import sys
import threading
import time
import traceback
import types
from datetime import datetime
from pathlib import Path

try:
    import resource
except ImportError:  # Windows, for --dry-run only
    resource = None

PILOT = Path(__file__).resolve().parent
ROOT = PILOT.parent
sys.path.insert(0, str(PILOT))
import probe_system  # noqa: E402

AUTHORS_DIR = ROOT / "authors" / "experiments" / "game24"
AUTHORS_FILE = AUTHORS_DIR / "game24_icrl.py"
DEFAULT_TOT = PILOT / "runs" / "_deps" / "tree-of-thought-llm" / "src"
GPU_SAMPLE_SECONDS = 10
KV_POLL_SECONDS = 5
GPU_FIELDS = ["index", "utilization.gpu", "memory.used", "memory.total", "power.draw", "temperature.gpu"]
THROTTLE_FIELD = "clocks_throttle_reasons.active"


class BudgetReached(Exception):
    """Raised at the start of a round when --max-minutes has passed."""


def progress(message):
    # sys.stderr is redirected to the log during the run.
    print(f"[pilot {datetime.now():%H:%M:%S}] {message}", file=sys.__stderr__, flush=True)


class GpuSampler:
    """Write `nvidia-smi -l` output to JSONL from a background thread."""

    def __init__(self, path):
        self.path = path
        self.process = None
        self.thread = None

    def start(self):
        fields = list(GPU_FIELDS)
        # Newer drivers may drop the old field name; an unknown field fails the whole query.
        if probe_system.run(["nvidia-smi", f"--query-gpu={THROTTLE_FIELD}", "--format=csv,noheader"]) is not None:
            fields.append(THROTTLE_FIELD)
        try:
            self.process = subprocess.Popen(
                ["nvidia-smi", f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits",
                 "-l", str(GPU_SAMPLE_SECONDS)],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
        except OSError:
            progress("nvidia-smi not found: no GPU samples")
            return
        self.thread = threading.Thread(target=self._write, args=(fields,), daemon=True)
        self.thread.start()

    def _write(self, fields):
        start = time.monotonic()
        with builtins.open(self.path, "w") as f:
            for line in self.process.stdout:
                values = [probe_system.to_number(v.strip()) for v in line.split(",")]
                row = {"t": round(time.monotonic() - start), **dict(zip(fields, values))}
                f.write(json.dumps(row) + "\n")
                f.flush()

    def stop(self):
        if self.process:
            self.process.terminate()
            self.thread.join(timeout=5)


class Recorder:
    """Collect one record per generate call, into rounds.jsonl."""

    def __init__(self, path, raw_dir, start, max_seconds):
        self.file = builtins.open(path, "w")
        self.raw_dir = raw_dir
        self.start = start
        self.max_seconds = max_seconds
        self.round = -1
        self.last_end = None
        self.metrics_error = None

    def raw_bytes(self):
        return sum(p.stat().st_size for p in self.raw_dir.iterdir() if p.is_file() and p.suffix != ".log")

    def write(self, record):
        self.file.write(json.dumps(record) + "\n")
        self.file.flush()


def read_engine_metrics(llm, recorder):
    """Return (preemptions, kv_cache_usage), or (None, None) if vLLM does not expose them."""
    try:
        metrics = llm.get_metrics()
    except Exception as exc:
        recorder.metrics_error = f"{type(exc).__name__}: {exc}"
        return None, None
    preemptions, usage = None, None
    for metric in metrics:
        if "num_preemptions" in metric.name:
            preemptions = (preemptions or 0) + getattr(metric, "value", 0)
        elif "cache_usage_perc" in metric.name:
            usage = getattr(metric, "value", None)
    return preemptions, usage


class InstrumentedLLM:
    def __init__(self, real_llm, recorder):
        self.llm = real_llm
        self.recorder = recorder

    def _poll_kv_cache(self, stop, peaks):
        while not stop.wait(KV_POLL_SECONDS):
            _, usage = read_engine_metrics(self.llm, self.recorder)
            if usage is not None:
                peaks.append(usage)

    def generate(self, prompts, sampling_params, **kwargs):
        rec = self.recorder
        # The authors use temperature 0.6 for the policy and 0.0 for the judge.
        phase = "policy" if sampling_params.temperature > 0 else "judge"
        if phase == "policy":
            if time.monotonic() - rec.start > rec.max_seconds:
                raise BudgetReached()
            rec.round += 1

        begin = time.monotonic()
        gap = begin - rec.last_end if rec.last_end is not None else None
        preempt_before, _ = read_engine_metrics(self.llm, rec)
        stop, peaks = threading.Event(), []
        poller = threading.Thread(target=self._poll_kv_cache, args=(stop, peaks), daemon=True)
        poller.start()
        kwargs.setdefault("use_tqdm", False)
        try:
            outputs = self.llm.generate(prompts, sampling_params, **kwargs)
        finally:
            stop.set()
            poller.join()
        seconds = time.monotonic() - begin
        rec.last_end = time.monotonic()
        preempt_after, _ = read_engine_metrics(self.llm, rec)

        prompt_tokens = [len(o.prompt_token_ids) for o in outputs]
        gen_tokens = [len(o.outputs[0].token_ids) for o in outputs]
        reasons = [o.outputs[0].finish_reason for o in outputs]
        record = {
            "round": rec.round,
            "phase": phase,
            "elapsed_s": round(rec.last_end - rec.start, 2),
            "seconds": round(seconds, 3),
            "gap_before_s": round(gap, 3) if gap is not None else None,
            "n_prompts": len(prompts),
            "max_tokens": sampling_params.max_tokens,
            "prompt_tokens_sum": sum(prompt_tokens),
            "prompt_tokens_max": max(prompt_tokens),
            "gen_tokens_sum": sum(gen_tokens),
            "gen_tokens_max": max(gen_tokens),
            "gen_tok_per_s": round(sum(gen_tokens) / seconds, 1) if seconds else None,
            "finish_length": reasons.count("length"),
            "finish_stop": reasons.count("stop"),
            "preemptions": (
                preempt_after - preempt_before
                if preempt_after is not None and preempt_before is not None else None
            ),
            "kv_cache_peak": max(peaks) if peaks else None,
            "peak_rss_gb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 ** 2, 2) if resource else None,
            "raw_output_bytes": rec.raw_bytes(),
        }
        rec.write(record)
        if phase == "judge":
            progress(
                f"round {rec.round}: judge {seconds:.0f}s, {sum(gen_tokens)} tokens, "
                f"{reasons.count('length')}/{len(reasons)} hit max_tokens, "
                f"elapsed {(rec.last_end - rec.start) / 60:.1f} min"
            )
        else:
            progress(
                f"round {rec.round}: policy {seconds:.0f}s, prompt max {max(prompt_tokens)} tokens, "
                f"{reasons.count('length')}/{len(reasons)} hit max_tokens"
            )
        return outputs


def patch_llm(args, recorder, run_info):
    """Replace vllm.LLM, recording the values the authors hard-coded and what we used instead."""
    import vllm

    real_llm_class = vllm.LLM

    def make_llm(*_, **authors_kwargs):
        run_info["authors_llm_kwargs"] = authors_kwargs
        kwargs = dict(
            model=args.model,
            tensor_parallel_size=args.gpus,
            gpu_memory_utilization=args.gpu_mem_util,
            seed=args.seed,
            disable_log_stats=False,  # needed by get_metrics()
        )
        run_info["llm_kwargs"] = kwargs
        progress(f"loading {args.model} on {args.gpus} GPU(s)...")
        begin = time.monotonic()
        llm = real_llm_class(**kwargs)
        run_info["model_load_s"] = round(time.monotonic() - begin, 1)
        write_run_info(args.results_dir, run_info)
        progress(f"model loaded in {run_info['model_load_s']}s")
        return InstrumentedLLM(llm, recorder)

    vllm.LLM = make_llm


def import_authors_module():
    spec = importlib.util.spec_from_file_location("game24_icrl", AUTHORS_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def redirect_writes(module, raw_dir):
    def redirected_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in "wax+"):
            file = raw_dir / Path(file).name
        return builtins.open(file, mode, *args, **kwargs)

    module.open = redirected_open
    module.os = types.SimpleNamespace(makedirs=lambda *_, **__: None)


def write_run_info(results_dir, run_info):
    (results_dir / "run.json").write_text(json.dumps(run_info, indent=2, default=str) + "\n")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="Qwen/Qwen3-32B")
    parser.add_argument("--gpus", type=int, default=None, help="default: all GPUs visible to nvidia-smi")
    parser.add_argument("--gpu-mem-util", type=float, default=0.95, help="the authors use 0.95")
    parser.add_argument("--rounds", type=int, default=51, help="the authors use 51")
    parser.add_argument("--max-minutes", type=float, default=float("inf"), help="stop cleanly at the next round")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--tot-path", type=Path, default=DEFAULT_TOT, help="tree-of-thought-llm/src")
    parser.add_argument("--dry-run", action="store_true", help="fake backend, no GPU, nothing for git")
    return parser.parse_args()


def main():
    args = parse_args()
    # Otherwise a new terminal without HF_HOME silently downloads the model again into ~/.cache.
    if not args.dry_run and "HF_HOME" not in os.environ and not Path(args.model).exists():
        sys.exit("Set HF_HOME, or pass a local folder as --model: see 'Where the model lives' in pilot/README.md")
    start = time.monotonic()
    system = probe_system.collect(disk_test_mb=0 if args.dry_run else 256, query_network=False)
    if args.gpus is None:
        args.gpus = max(system["gpu"]["count"], 1)

    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    model_slug = args.model.split("/")[-1].lower()
    run_id = f"{stamp}_{probe_system.gpu_slug(system)}_{model_slug}_s{args.seed}"
    raw_dir = PILOT / "runs" / run_id
    # A dry run is only a test of this tool: it stays out of the folder committed to git.
    args.results_dir = (raw_dir / "results") if args.dry_run else (PILOT / "results" / run_id)
    raw_dir.mkdir(parents=True, exist_ok=True)
    args.results_dir.mkdir(parents=True, exist_ok=True)
    (args.results_dir / "system.json").write_text(json.dumps(system, indent=2) + "\n")

    run_info = {
        "run_id": run_id,
        "status": "running",  # left as is if the session is killed
        "dry_run": args.dry_run,
        "argv": sys.argv,
        "started": datetime.now().isoformat(timespec="seconds"),
        "rounds_requested": args.rounds,
        "max_minutes": None if args.max_minutes == float("inf") else args.max_minutes,
        "model": args.model,
        "seed": args.seed,
        "raw_dir": raw_dir.relative_to(ROOT).as_posix(),
        "authors_file_sha256": hashlib.sha256(AUTHORS_FILE.read_bytes()).hexdigest(),
    }
    write_run_info(args.results_dir, run_info)
    progress(f"run {run_id}, results in {args.results_dir}")

    recorder = Recorder(args.results_dir / "rounds.jsonl", raw_dir, start, args.max_minutes * 60)
    sampler = GpuSampler(args.results_dir / "gpu_samples.jsonl")
    sampler.start()

    os.environ.setdefault("VLLM_LOGGING_LEVEL", "WARNING")
    sys.path.insert(0, str(args.tot_path))
    if args.dry_run:
        import fake_backend

        fake_backend.install()
    os.chdir(AUTHORS_DIR)  # the authors read game24_3steps.txt from the working directory

    try:
        # Explicit encoding: the authors print non-ASCII characters and the locale may not be UTF-8.
        with builtins.open(raw_dir / "authors_output.log", "w", encoding="utf-8", errors="replace") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                patch_llm(args, recorder, run_info)
                module = import_authors_module()
                redirect_writes(module, raw_dir)
                module.evaluate_checkpoint(base_model_id=args.model, n=args.rounds)
        run_info["status"] = "completed"
    except BudgetReached:
        run_info["status"] = "budget_reached"
    except BaseException as exc:
        # An out-of-memory crash is a result too: keep it in the record.
        run_info["status"] = "crashed"
        run_info["error"] = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[-4000:]
        progress(run_info["error"])
    finally:
        sampler.stop()
        run_info["finished"] = datetime.now().isoformat(timespec="seconds")
        run_info["total_seconds"] = round(time.monotonic() - start, 1)
        run_info["rounds_completed"] = recorder.round + 1 if run_info["status"] != "crashed" else None
        run_info["last_round_started"] = recorder.round
        run_info["tail_seconds_after_last_generate"] = (
            round(time.monotonic() - recorder.last_end, 2) if recorder.last_end else None
        )
        run_info["metrics_error"] = recorder.metrics_error
        run_info["raw_output_bytes"] = recorder.raw_bytes()
        write_run_info(args.results_dir, run_info)
        progress(f"{run_info['status']} after {run_info['total_seconds'] / 60:.1f} min")
        progress(f"next: python pilot/summarize.py {args.results_dir}")
    return 0 if run_info["status"] in ("completed", "budget_reached") else 1


if __name__ == "__main__":
    sys.exit(main())
