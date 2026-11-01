**Claim 1: Model Size and Judge Quality in ICRL**

**1. What the project is about:**

**Generalization.** The paper shows ICRL on Game of 24 with one model, GPT-4.1, which also grades its own attempts. We test whether the improvement over rounds holds for a smaller and a larger open model. We also test whether it depends on how good the judge is. The paper suggests that self-evaluation limits performance compared with external feedback, but does not test this.

Our question: Does ICRL’s improvement on Game of 24 depend on model size, and how much does it depend on the quality of the judge? The paper raises the second point as a hypothesis but tests neither.

**2. Baselines**

We compare two models and two kinds of judge:

|                       | Self-judge (paper’s setting) | Oracle judge |
| --------------------- | ---------------------------- | ------------ |
| Small Qwen3 (e.g. 8B) | ICRL                         | ICRL         |
| Qwen3-32B             | ICRL (shared with Claim 2)   | ICRL         |

- Oracle judge: an exact step score computed by brute force (is 24 still reachable from the remaining numbers?). This stands for perfect external feedback.
- Best-of-N for both models, with the same number of attempts, as the baseline that uses no learning.
- Optional, if time allows: one model from another family, comparing ICRL (self-judge) with Best-of-N.

**3. Evaluation protocol**

We keep the paper’s setup: the step-scoring prompt, ICRL Preset instructions and the rule-based correctness check. We report:

- Per-round and running-max success rate, as in the paper.
- The gain of ICRL over Best-of-N for each of the four cells.
- Judge accuracy: how often each model’s step scores match the exact scores. This is computed from saved logs and needs no extra runs.

Results are reported as mean ± standard error over 3 seeds. All configurations use the same problems and number of rounds.

**4. Theorem/proof targets**

Not applicable.

**5. Test instances**

The paper’s 100 Game of 24 problems (Tree of Thoughts dataset, indices 900–999)

**6. Compute budget**

We use the authors’ code with vLLM. The plan is about 15 runs: 3 ICRL configurations, plus Best-of-N for 2 models, each with 3 seeds. The 32B self-judge runs are reused from Claim 2. Oracle-judge runs are cheaper than the paper’s setup because they need no judge calls. We will fix the number of rounds (30–50) and model sizes after a pilot run this week.

**7. Expected limitations**

- The small model may fail the answer format; we report the failure rate separately.
- Qwen3’s built-in reasoning mode is turned off, so the task is not solved in a single pass.
- We test one model family on one task, so we draw conclusions about trends, not about matching the paper’s numbers.

**Claim 2: Ablation Study of In-Context Window Size**

\- What the project is about:

1. **Ablation**. The paper reports that ICRL performs worse when only the last three attempts are kept instead of the full history. We reproduce this on Game of 24 and, if the computational power allows, test more history sizes. We also check whether a longer history is still worth it under a fixed token budget.Generalization. We use the model chosen by our group. If it differs from GPT-4.1, this also tests whether the effect holds for another model.
2.  **Baselines**

\- k = all: Full history (paper's default).

\- k = 3: Last three attempts (paper's ablation).

\- k = 0: No history, similar to Best-of-N.

Optional, if the compute power allows: k = 1, 5, 10. The comparison of k = all and k = 3 is the reproduction; the rest are extensions.

1. **Evaluation protocol**

We keep the paper's setup: the model uses its own self-evaluation rewards, and correctness is checked separately with a rule-based checker. We report:

- Per-round and running-max success rate, as in the paper (Figures 2, 3, 13, 14).
- Success rate against tokens used, comparing history sizes at the same number of rounds and at the same token budget (counting  prompts, responses and self-evaluation calls).

Results are given as mean and standard error over three seeds, with the same problems and number of rounds for all configurations.

1. **Theorem/proof targets**

​      Not applicable.

1. **Test instances**

The paper's 100 Game of 24 problems (Tree of Thoughts dataset, indices 900–999 in the authors' code).

1.  **Compute budget**

We reuse the authors' implementation, which supports vLLM (Qwen3-32B on two GPUs by default) and API models; the history size is a parameter in the code. Minimum plan: 3 history sizes × 3 seeds = 9 runs. Rounds and GPU needs will be fixed after a pilot run and discussed with our supervisor. If running the model locally is not feasible, we discuss an API alternative.

1. **Expected limitations**

A different or smaller model may give different numbers and weaker self-evaluation rewards. We therefore focus on whether the trend between history sizes holds, not on matching the paper's exact results, and document all deviations.

**Claim 3: Does ICRL Use the Reward Signal or the Word "Reward"?**

**1. What the project is about**

**Ablation.** In ICRL each past attempt is shown with its step scores labelled `<Reward: x>` and a total labelled `Return`, and the instructions ask for "higher rewards". The paper shows that removing the scores hurts (Zero Rewards, Exploration Only), but it never separates two explanations: the model may use the *numbers*, or it may react to the *RL vocabulary* around them. The authors' code contains a prompt-variant script for creative writing (Reward → Score, attempt → trial), but the paper does not report it.

Our question: on Game of 24, how much of ICRL's gain over Best-of-N comes from the numerical feedback, and how much from labelling it as a reward?

We go deep on one task instead of broad. Note that the ICRL Preset instructions never contain the words "explore" or "exploit" (only the Autonomous instruction does), so the main manipulation is the reward vocabulary; explore/exploit wording is an optional extension.

**Hypotheses**

- H1 (signal): with the paper's wording, true scores beat shuffled scores.
- H2 (label): with true scores, neutral labels ("Score", "Total") perform the same as "Reward"/"Return".
- H3 (direction): if scores are shown as "Regret" (lower is better), the model still moves toward the best attempts. If it does not, it follows the "higher number is better" pattern rather than the meaning of the label.

**2. Variables**

*Experimental (independent) variables*

| Variable | Levels |
| --- | --- |
| A. Label wording | `Reward`/`Return` (paper) · `Score`/`Total` (neutral) · `Regret` (= max − score, "lower is better"; extension) |
| B. Feedback signal | true scores · shuffled scores (each attempt shows the scores of another attempt of the same problem, so the distribution is kept but the link to quality is broken) |

Only the label words and, for Regret, the direction words ("higher" → "lower") change. The instructions are otherwise identical, word for word.

*Control variables (kept fixed across all conditions)*

- Model and decoding: the main Qwen3 model from Claim 1, reasoning mode off, same temperature, top-p and max tokens.
- Judge: the exact oracle step score from Claim 1, so the scores cannot depend on the wording. The paper's self-judge prompt never uses the word "reward", so self-judge runs are possible as a check.
- ICRL setup: ICRL Preset (explore/exploit alternation), full history (k = all, as Claim 2's default), same `<attempt>` format, answer format and number of rounds.
- Problems and seeds: the same 100 problems and the same 3 seeds in every condition.
- Success is always measured with the rule-based checker, never with the displayed scores.

*Measured (dependent) variables*

- Primary: running-max success rate at the final round, and the gain over Best-of-N.
- Secondary: per-round success rate; duplicate rate (attempts identical to an earlier one); copy-of-best rate (share of exploitation rounds whose first step matches the best-scored previous attempt); format failure rate.

**3. Conditions**

|                | True scores                    | Shuffled scores |
| -------------- | ------------------------------ | --------------- |
| Reward/Return  | C0, paper (shared with Claim 1, oracle cell) | C2 |
| Score/Total    | C1                             | C3              |
| Regret (ext.)  | C4                             | –               |

Baselines: Best-of-N with the same number of attempts (shared with Claim 1) as the no-learning floor.

The 2×2 design separates the effects. C0 vs C2 measures the signal, C0 vs C1 the label, and the interaction tells us whether the signal is only used when it is called a reward.

**4. Evaluation protocol**

- *Full runs.* Each condition runs the full ICRL loop. We report the curves as in the paper (per-round and running max) and the final running-max success, as mean ± standard error over 3 seeds.
- *Frozen-context probe.* In full runs, trajectories drift apart after the first round, so a difference can grow from noise. To measure the wording effect directly, we take saved histories from C0 at fixed rounds (e.g. 5, 15, 30), rewrite only the labels for each condition, and sample one next attempt several times. The contexts then differ only in the words. We measure next-attempt success and copy-of-best rate. For Regret, this is the manipulation check: does the model copy the lowest-regret attempt or the highest?
- *Statistics.* Comparisons are paired over the 100 problems. We report the difference in final running-max success with a bootstrap 95% confidence interval.

**5. Theorem/proof targets**

Not applicable.

**6. Test instances**

The paper's 100 Game of 24 problems (Tree of Thoughts dataset, indices 900–999), as in Claims 1 and 2.

**7. Compute budget**

Core design: 4 conditions × 3 seeds = 12 runs, of which C0 is reused from Claim 1, so 9 new runs. Regret adds 3 runs. The oracle judge needs no judge calls, so each run is cheaper than the paper's. The frozen-context probe uses single generations only (about 100 problems × 3 rounds × 4 wordings × 8 samples), roughly the cost of one or two runs. The changes to the code are small: the label strings and the score shuffling, both in the prompt-building loop of `game24_icrl.py`.

Optional, if time allows: (a) ICRL Autonomous with and without the words "exploration/exploitation", keeping the same operational description; (b) creative writing with the authors' unreported variant script, as a second-task check.

**8. Expected limitations**

- If ICRL gives no clear gain over Best-of-N for our model, there is nothing to ablate. The pilot from Claim 1 decides which model size we use.
- Paraphrasing can change more than the label (length, tone). We keep the paraphrases minimal and word-for-word otherwise.
- Shuffled scores still give the model numbers to attend to, so C2/C3 test misleading feedback, not absent feedback. The paper's Zero Rewards ablation covers the absent case.
- One model family and one task: we draw conclusions about which effect dominates, not general ones.
