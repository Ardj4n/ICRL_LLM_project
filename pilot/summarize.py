"""Turn the measurements of one pilot run into summary.md and success_by_round.json.

Reads rounds.jsonl, gpu_samples.jsonl and run.json from the results folder, and
the authors' output_list.json from the raw folder, if it is still there.
It does not decide anything: the projections are starting points for the discussion.
"""
import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_ROUNDS_TO_FIT = 3


def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass  # last line of a killed run
    return rows


def hours(seconds):
    return f"{seconds / 3600:.2f} h"


def by_round(rows, phase):
    return {r["round"]: r for r in rows if r["phase"] == phase}


def complete_rounds(rows):
    """Rounds where both policy and judge finished."""
    policy, judge = by_round(rows, "policy"), by_round(rows, "judge")
    return sorted(set(policy) & set(judge))


def phase_seconds(rows):
    """Seconds per round for each phase. "other" is the gap before the next round's policy."""
    policy, judge = by_round(rows, "policy"), by_round(rows, "judge")
    rounds = complete_rounds(rows)
    other = {}
    for r in rounds:
        # CPU work after the judge: answer checks and saving output_list.json.
        if r + 1 in policy and policy[r + 1]["gap_before_s"] is not None:
            other[r] = policy[r + 1]["gap_before_s"]
    return (
        {r: policy[r]["seconds"] for r in rounds},
        {r: judge[r]["seconds"] for r in rounds},
        other,
    )


def project(series, target_rounds):
    """Sum of seconds over target_rounds: measured rounds, plus a straight-line fit for the rest."""
    if not series:
        return None
    measured = sum(v for r, v in series.items() if r < target_rounds)
    missing = [r for r in range(target_rounds) if r not in series]
    if not missing:
        return measured
    if len(series) < MIN_ROUNDS_TO_FIT:
        return None
    slope, intercept = statistics.linear_regression(list(series), list(series.values()))
    return measured + sum(max(intercept + slope * r, 0) for r in missing)


def scenarios(rows, target_rounds):
    """Estimated hours for one run of each kind planned in the proposal."""
    policy, judge, other = phase_seconds(rows)
    if not policy:
        return []
    total_policy = project(policy, target_rounds)
    total_other = project(other, target_rounds) or 0
    mean_judge = statistics.mean(judge.values())
    mean_other = statistics.mean(other.values()) if other else 0
    total_judge = mean_judge * target_rounds  # judge prompts do not grow with the history

    def history_cost(k):
        """Policy seconds per round when only k attempts are in the prompt.

        Round r has r attempts in its prompt. Two rounds cover both instructions, which alternate.
        """
        near = [policy[r] for r in (k, k + 1) if r in policy]
        return statistics.mean(near) if near else policy[max(policy)]

    result = []
    if total_policy is not None:
        result.append(("Full history, self-judge", total_policy + total_judge + total_other))
        result.append(("Full history, oracle judge (no judge calls)", total_policy + total_other))
    for k, label in [(3, "k = 3, self-judge"), (0, "k = 0, self-judge")]:
        result.append((label, (history_cost(k) + mean_judge + mean_other) * target_rounds))
    result.append(("k = 0, no judge calls (Best-of-N)", (history_cost(0) + mean_other) * target_rounds))
    return result


def gpu_summary(samples):
    per_gpu = defaultdict(list)
    for sample in samples:
        per_gpu[sample.get("index")].append(sample)
    table = []
    for index, rows in sorted(per_gpu.items(), key=lambda kv: str(kv[0])):
        numeric = lambda field: [r[field] for r in rows if isinstance(r.get(field), (int, float))]  # noqa: E731
        util, mem, power, temp = (numeric(f) for f in
                                  ("utilization.gpu", "memory.used", "power.draw", "temperature.gpu"))
        total = numeric("memory.total")
        table.append({
            "index": index,
            "samples": len(rows),
            "util_mean": statistics.mean(util) if util else None,
            "mem_peak_gib": max(mem) / 1024 if mem else None,
            "mem_total_gib": max(total) / 1024 if total else None,
            "power_max": max(power) if power else None,
            "temp_max": max(temp) if temp else None,
            "throttle_codes": Counter(str(r.get("clocks_throttle_reasons.active")) for r in rows),
        })
    return table


def success_by_round(raw_dir):
    """Success is our reading of the authors' reward fields: right value and all four numbers used once."""
    path = raw_dir / "output_list.json"
    if not path.exists():
        return None
    problems = json.loads(path.read_text())
    n_rounds = max((len(p) for p in problems), default=0)
    solved = [False] * len(problems)
    curve = []
    for r in range(n_rounds):
        hits, format_failures, empty = 0, 0, 0
        for i, problem in enumerate(problems):
            if r >= len(problem):
                continue
            entry = problem[r]
            good = float(entry["accuracy_reward"]) == 0 and float(entry["format_reward"]) == 0
            hits += good
            solved[i] = solved[i] or good
            format_failures += float(entry["format_reward"]) != 0
            empty += not entry["model_answer"]
        curve.append({
            "round": r,
            "solved": hits,
            "solved_so_far": sum(solved),
            "format_failures": format_failures,
            "no_answer_tag": empty,
            "n_problems": len(problems),
        })
    return curve


def phase_row(name, rows):
    if not rows:
        return f"| {name} | – | – | – | – | – | – |"
    seconds = sum(r["seconds"] for r in rows)
    gen = sum(r["gen_tokens_sum"] for r in rows)
    calls = sum(r["n_prompts"] for r in rows)
    truncated = sum(r["finish_length"] for r in rows)
    known = [r["preemptions"] for r in rows if r["preemptions"] is not None]
    preempt = sum(known) if known else "n/a"
    return (
        f"| {name} | {hours(seconds)} | {seconds / len(rows):.1f} | {gen / seconds if seconds else 0:.0f} | "
        f"{gen / calls:.0f} | {100 * truncated / calls:.1f}% | {preempt} |"
    )


def build_report(results_dir, target_rounds):
    info = json.loads((results_dir / "run.json").read_text())
    system_path = results_dir / "system.json"
    system = json.loads(system_path.read_text()) if system_path.exists() else {}
    rows = read_jsonl(results_dir / "rounds.jsonl")
    samples = read_jsonl(results_dir / "gpu_samples.jsonl")
    done = complete_rounds(rows)

    lines = [f"# Pilot run {info['run_id']}", ""]
    if info.get("dry_run"):
        lines += ["**Dry run with a fake backend: these numbers mean nothing.**", ""]
    gpu = system.get("gpu", {})
    gpu_names = ", ".join(sorted({g["name"] for g in gpu.get("gpus", [])})) or "none"
    # A killed run never wrote its totals: fall back to the last record.
    last = rows[-1] if rows else {}
    total_seconds = info.get("total_seconds") or last.get("elapsed_s", 0)
    raw_bytes = info.get("raw_output_bytes") or last.get("raw_output_bytes", 0)
    lines += [
        f"- **Status:** {info['status']}, {len(done)} of {info['rounds_requested']} rounds complete",
        f"- **Model:** {info['model']}, seed {info['seed']}",
        f"- **GPUs:** {gpu.get('count', 0)} × {gpu_names}, "
        f"{gpu.get('total_memory_mib', 0) / 1024:.0f} GiB in total",
        f"- **Total time:** {hours(total_seconds)}; "
        f"model load {info.get('model_load_s', 'n/a')} s",
        f"- **Raw output size:** {raw_bytes / 1e6:.0f} MB for this run",
    ]
    if info.get("metrics_error"):
        lines.append(f"- **vLLM metrics unavailable:** {info['metrics_error']}")
    if info["status"] == "crashed" and info.get("error"):
        lines += ["", "## Crash", "", "```", info["error"].strip()[-1500:], "```"]
    if info["status"] == "running":
        lines += ["", "**The run never recorded an end: the session was probably killed or paused.**"]

    lines += [
        "", "## Cost by phase", "",
        "| Phase | Total | s/round | gen tok/s | gen tokens/call | Hit max_tokens | Preemptions |",
        "| --- | --- | --- | --- | --- | --- | --- |",
        phase_row("Policy", [r for r in rows if r["phase"] == "policy"]),
        phase_row("Judge", [r for r in rows if r["phase"] == "judge"]),
    ]
    _, _, other = phase_seconds(rows)
    if other:
        lines += ["", f"CPU work between rounds (answer checks, saving): {hours(sum(other.values()))} in total, "
                      f"{min(other.values()):.1f}–{max(other.values()):.1f} s/round."]

    policy = by_round(rows, "policy")
    if done:
        marks = sorted({done[0], done[len(done) // 2], done[-1]})
        lines += [
            "", "## Growth over rounds", "",
            "| Round | Policy s | Judge s | Largest prompt (tokens) | KV cache peak | Peak RSS (GiB) |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        judge = by_round(rows, "judge")
        for r in marks:
            kv = policy[r]["kv_cache_peak"]
            lines.append(
                f"| {r} | {policy[r]['seconds']:.1f} | {judge[r]['seconds']:.1f} | "
                f"{policy[r]['prompt_tokens_max']} | {'n/a' if kv is None else f'{kv:.2f}'} | "
                f"{judge[r]['peak_rss_gb']} |"
            )

    gpus = gpu_summary(samples)
    if gpus:
        lines += [
            "", "## GPU during the run", "",
            "| GPU | Samples | Mean util % | Peak memory (GiB) | Max power (W) | Max temp (°C) | Throttle codes |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for g in gpus:
            codes = ", ".join(f"{code} ×{count}" for code, count in g["throttle_codes"].most_common())
            util = "n/a" if g["util_mean"] is None else f"{g['util_mean']:.0f}"
            mem = "n/a" if g["mem_peak_gib"] is None else f"{g['mem_peak_gib']:.1f} / {g['mem_total_gib']:.0f}"
            lines.append(f"| {g['index']} | {g['samples']} | {util} | {mem} | {g['power_max']} | "
                         f"{g['temp_max']} | {codes} |")

    estimates = scenarios(rows, target_rounds)
    if estimates:
        lines += [
            "", f"## Estimated hours for one {target_rounds}-round run", "",
            "**Estimates, not measurements**, for 100 problems on this machine. Rounds not reached are "
            "extrapolated with a straight line, which cannot foresee a slowdown from a full KV cache. "
            "Short-history rows reuse the early rounds of this run.", "",
            "| Run type | Hours |", "| --- | --- |",
        ]
        lines += [f"| {label} | {seconds / 3600:.2f} |" for label, seconds in estimates]

    raw_dir = ROOT / info["raw_dir"]
    curve = success_by_round(raw_dir)
    if curve is not None:
        (results_dir / "success_by_round.json").write_text(json.dumps(curve, indent=1) + "\n")
    else:
        saved = results_dir / "success_by_round.json"
        curve = json.loads(saved.read_text()) if saved.exists() else None
    if curve:
        step = max(len(curve) // 5, 1)
        marks = sorted(set(range(0, len(curve), step)) | {len(curve) - 1})
        lines += [
            "", "## Success (setup check)", "",
            "Success is `accuracy_reward == 0` and `format_reward == 0`. The authors' own success script "
            "is not in their repository, so this is our reading. One seed: not a result.", "",
            "| Round | Solved | Solved so far | Format failures | No answer tag |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines += [
            f"| {curve[r]['round']} | {curve[r]['solved']} | {curve[r]['solved_so_far']} | "
            f"{curve[r]['format_failures']} | {curve[r]['no_answer_tag']} |"
            for r in marks
        ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_dir", type=Path)
    parser.add_argument("--target-rounds", type=int, default=51, help="rounds of the run to estimate")
    args = parser.parse_args()
    report = build_report(args.results_dir, args.target_rounds)
    (args.results_dir / "summary.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
