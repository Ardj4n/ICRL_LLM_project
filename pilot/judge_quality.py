"""Compare pilot runs: do the judge's scores mean anything, and what does a round cost?

Reads the authors' output_list.json from the raw folder and rounds.jsonl from the results
folder. Each step score is checked against an exact brute-force oracle: is 24 still reachable
from the numbers the step says are left? Writes judge_quality.json next to the results, so it
survives the loss of the raw folder, and prints one Markdown table for all the runs given.
"""
import argparse
import json
import re
from collections import Counter
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEFT = re.compile(r"\(left:\s*([^)]*)\)")
NUMBER = re.compile(r"\d+(?:\.\d+)?(?:/\d+)?")
# The same pattern as the authors' parser: it takes the first match.
SCORE = re.compile(r"\*\*Answer\*\*\s*:\s*([+-]?\d+)")


@lru_cache(maxsize=None)
def reachable(numbers):
    """Exact: can these numbers, each used once, make 24 with + - * /?"""
    if len(numbers) == 1:
        return numbers[0] == 24
    for i, j in combinations(range(len(numbers)), 2):
        a, b = numbers[i], numbers[j]
        rest = [numbers[k] for k in range(len(numbers)) if k not in (i, j)]
        results = {a + b, a - b, b - a, a * b}
        if b:
            results.add(a / b)
        if a:
            results.add(b / a)
        if any(reachable(tuple(sorted(rest + [r]))) for r in results):
            return True
    return False


def left_numbers(answer):
    """The numbers after each step, or None if the answer does not have exactly three steps."""
    steps = LEFT.findall(answer)
    if len(steps) != 3:
        return None
    try:
        parsed = [tuple(sorted(Fraction(n) for n in NUMBER.findall(step))) for step in steps]
    except (ValueError, ZeroDivisionError):
        return None
    return parsed if all(parsed) else None


def rate(hits, total):
    return hits / total if total else None


def judge_stats(problems):
    step_true_pos = step_true_neg = step_pos = step_neg = 0
    final_right = final_total = answered = responses = unparsed = 0
    returns = {"solved": [], "wrong": [], "empty": []}
    empty = attempts = format_failures = 0
    solved_authors, solved_strict = [set() for _ in range(2)]
    curve = []
    for r in range(max((len(p) for p in problems), default=0)):
        hits_authors = hits_strict = 0
        for index, problem in enumerate(problems):
            if r >= len(problem):
                continue
            entry = problem[r]
            attempts += 1
            answer = entry["model_answer"]
            right_value = float(entry["accuracy_reward"]) == 0
            right_numbers = float(entry["format_reward"]) == 0
            solved = right_value and right_numbers
            hits_authors += right_value
            hits_strict += solved
            if right_value:
                solved_authors.add(index)
            if solved:
                solved_strict.add(index)
            format_failures += not right_numbers
            empty += not answer.strip()
            kind = "empty" if not answer.strip() else ("solved" if solved else "wrong")
            returns[kind].append(float(entry["gpt_eval_return"]))

            scores = [float(s) for s in entry["gpt_eval_reward_list"]]
            responses += len(entry["gpt_eval_response"])
            answered += sum(bool(SCORE.search(t)) for t in entry["gpt_eval_response"])
            if kind == "empty":
                continue
            final_total += 1
            final_right += (scores[3] > 0) == solved
            steps = left_numbers(answer)
            if steps is None:
                unparsed += 1
                continue
            for numbers, score in zip(steps, scores[:3]):
                if reachable(numbers):
                    step_pos += 1
                    step_true_pos += score > 0
                else:
                    step_neg += 1
                    step_true_neg += score == 0
        curve.append({"round": r, "authors": hits_authors, "authors_so_far": len(solved_authors),
                      "strict": hits_strict, "strict_so_far": len(solved_strict)})
    recall, specificity = rate(step_true_pos, step_pos), rate(step_true_neg, step_neg)
    return {
        "attempts": attempts,
        "empty_answers": rate(empty, attempts),
        "format_failures": rate(format_failures, attempts),
        "judge_gave_a_score": rate(answered, responses),
        "steps_checked": step_pos + step_neg,
        "steps_reachable": rate(step_pos, step_pos + step_neg),
        "attempts_without_3_steps": unparsed,
        "step_recall": recall,
        "step_specificity": specificity,
        "step_balanced_accuracy": (recall + specificity) / 2 if recall is not None and specificity is not None else None,
        "final_answer_accuracy": rate(final_right, final_total),
        "mean_return": {k: sum(v) / len(v) if v else None for k, v in returns.items()},
        "n_return": {k: len(v) for k, v in returns.items()},
        "by_round": curve,
    }


def cost_stats(rows):
    def phase(name):
        chosen = [r for r in rows if r["phase"] == name]
        seconds = sum(r["seconds"] for r in chosen)
        calls = sum(r["n_prompts"] for r in chosen)
        return {
            "rounds": len(chosen),
            "s_per_round": seconds / len(chosen) if chosen else None,
            "hit_max_tokens": rate(sum(r["finish_length"] for r in chosen), calls),
            "gen_tokens_per_call": rate(sum(r["gen_tokens_sum"] for r in chosen), calls),
            "gen_tok_per_s": rate(sum(r["gen_tokens_sum"] for r in chosen), seconds),
            "preemptions": sum(r["preemptions"] or 0 for r in chosen),
            "kv_cache_peak": max((r["kv_cache_peak"] or 0 for r in chosen), default=None),
            "prompt_tokens_max": max((r["prompt_tokens_max"] for r in chosen), default=None),
        }
    return {"policy": phase("policy"), "judge": phase("judge")}


def analyse(results_dir):
    info = json.loads((results_dir / "run.json").read_text())
    rows = []
    path = results_dir / "rounds.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # last line of a killed run
    report = {
        "run_id": info["run_id"],
        "model": info["model"],
        "status": info["status"],
        "method": info.get("method", "icrl"),
        "prompt_format": info.get("prompt_format", "raw"),
        "judge_thinking": info.get("judge_thinking", False),
        "model_load_s": info.get("model_load_s"),
        "error_tail": (info.get("error") or "").strip().splitlines()[-1][:300] if info.get("error") else None,
        "cost": cost_stats(rows),
    }
    output_list = ROOT / info["raw_dir"] / "output_list.json"
    if output_list.exists():
        report["judge"] = judge_stats(json.loads(output_list.read_text()))
    (results_dir / "judge_quality.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def pct(value):
    return "–" if value is None else f"{100 * value:.0f}%"


def num(value, digits=0):
    return "–" if value is None else f"{value:.{digits}f}"


def table(reports):
    lines = [
        "| Run | Status | Rounds | Policy s/round | Judge s/round | Policy cut | Judge cut | Empty answers | "
        "Judge gave score | Step bal. acc. | Final acc. | Return solved / wrong / empty | Strict so far |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in reports:
        policy, judge = r["cost"]["policy"], r["cost"]["judge"]
        quality = r.get("judge", {})
        returns = quality.get("mean_return", {})
        curve = quality.get("by_round", [])
        lines.append(
            f"| {r['run_id'].split('_', 2)[-1]} | {r['status']} | {judge['rounds']} | "
            f"{num(policy['s_per_round'])} | {num(judge['s_per_round'])} | "
            f"{pct(policy['hit_max_tokens'])} | {pct(judge['hit_max_tokens'])} | "
            f"{pct(quality.get('empty_answers'))} | {pct(quality.get('judge_gave_a_score'))} | "
            f"{pct(quality.get('step_balanced_accuracy'))} | {pct(quality.get('final_answer_accuracy'))} | "
            f"{num(returns.get('solved'), 1)} / {num(returns.get('wrong'), 1)} / {num(returns.get('empty'), 1)} | "
            f"{curve[-1]['strict_so_far'] if curve else '–'} |"
        )
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results_dirs", type=Path, nargs="+")
    args = parser.parse_args()
    print(table([analyse(d) for d in args.results_dirs]))


if __name__ == "__main__":
    main()
