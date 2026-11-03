# Journal

Concrete results, by day. Everything else is in `journal/`, linked under each day.

## 2026-11-03

- [Claim 2](CLAIM_2.md): each aspect of the claim, what this machine covers and what Renku needs.
- [To do](journal/2026-11-03_todo.md): tasks done and still open.
- [Decisions](journal/2026-11-03_decisions.md): the project's decisions, with options and recommendations.
- [Models](journal/2026-11-03_models.md): which models the paper uses, which fit 12 GB, and why 14B was dropped.
- [What is valid](journal/2026-11-03_validity.md): what the audit checked, what the runs can support, and what to declare in the report.
- [Why outputs are cut](journal/2026-11-03_truncation.md): the causes of truncation, with numbers and examples.
- [Pilot tools added](journal/2026-11-03_pilot_tools.md): new wrapper options, `judge_quality.py`, and where prompts are saved.

The chat template fixes the judge (`--prompt-format chat`: the model's template, thinking off; one seed, few rounds: not a result):

| | 8B-AWQ raw (2 rounds) | 8B-AWQ chat (3 rounds) | 4B-AWQ chat (3 rounds) |
| --- | --- | --- | --- |
| Minutes per round | ~15 | ~5.5 | ~3 |
| Policy answers empty | 64% | 1% | 35% |
| Judge gave a score | 43% | 96% | 79% |
| Judge cut at `max_tokens` | 94% | 4% | 16% |
| Step balanced accuracy, against an exact oracle | 45% | 89% | 79% |
| Mean return, solved / wrong | 13.0 / 3.2 | 16.7 / 1.4 | 15.9 / 1.8 |
| Solved so far, strict | 4 | 12 | 8 |

- Audit of the 8B chat run: no bug found. The authors' checker agrees with an independent one on 298 of 298 attempts, and the 30% format failures of 8B are real model errors.
- The judge is too generous on solutions: 10 for 32 attempts, 15 really solved (8B).
- Cuts with the chat template: policy 0 of 600; judge 48 of 1200 (8B) and 194 of 1200 (4B). 45 of the 47 cuts on real 8B attempts fall on unreachable steps, where the resulting 0 is right. 147 of the 194 cuts of 4B come from empty attempts.
- 14B-AWQ dropped, not tested: 10 GB of weights leave about no KV cache on 12 GB (estimate).
- Downloads were slow on 3 Nov, about 2.5 MB/s against 12 MB/s on 1 Nov, in WSL and Windows alike. WSL is not the cause. The clean line speed is still to be measured.

## 2026-11-02

- [Raw judge](journal/2026-11-02_judge_signal.md): how the judge's scores break with raw prompts, in detail.
- [Local GPU](journal/2026-11-02_local_gpu.md): the machine, and what it took to run on 12 GB.

- The pilot installs and runs on the local RTX 3060 in WSL2, with 4 more pins, `--gpu-mem-util 0.90` and `--max-model-len 24000`.
- Smoke test (`20261101-2336_...`, 2 rounds, 8B-AWQ, one seed: not a result): 30.9 min, 15 min/round: policy ~205 s, judge ~680 s. ~550 tokens/s. KV cache at 1.00 from round 0, 3599 preemptions.
- Straight-line estimate 12.9 h per 51-round run, ~270 h for 21 runs. Would change if the judge stops early.
- With raw prompts the judge's scores are mostly not real: 94% hit `max_tokens`, 54.6% contain no score, and the mean return is 7.1 for empty answers against 3.8 for real ones.

## 2026-11-01

- [Authors' code](journal/2026-11-01_authors_code.md): the pinned commit, how to sync it, and its known issues.
- [Pilot](journal/2026-11-01_pilot.md): what the pilot measures and where it has been tested.
- [Renku](journal/2026-11-01_renku.md): the first session's resources, and the commands to run the pilot.
- [Estimates](journal/2026-11-01_estimates.md): expected parallel requests by VRAM and run times, from before the pilot.

- Authors' code pinned to `43429cd` (tag `icrl-proposal-base`), with 7 API keys removed.
- Compute pilot written (`pilot/`, branch `pilot-compute`), tested on a fake backend only.
- First Renku session: no GPU, 8 cores, 31 GB RAM, 7.8 GB in `/home/renku/work`. The pilot cannot run there.

## 2026-10-27

- TA feedback: deep over broad; Claim 2 on track, Claim 3 interesting; discuss control and experimental variables.
- Claim 3 rewritten in `README.md` (uncommitted): Game of 24 only, label × true/shuffled scores, frozen-context probe.
- `PROPOSAL.md` added (`19a6b27`).

## 2026-10-21

- Repository set up; authors' code moved to `authors/` (`5058e3c`, `d6123d4`, `80e001a`).
