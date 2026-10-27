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

**Claim 3: Prompt Wording in ICRL (Reward vs. Regret, Exploration/Exploitation Terms)**

**What the project is about**

Ablation. The paper’s prompts depend on RL vocabulary: each score is labelled “Reward”, and the ICRL Preset alternates instructions that ask the model to “explore” or “exploit”. The paper never tests whether these words matter. We test whether ICRL’s improvement comes from the numerical signal itself or from the model recognising RL terms. We change only the wording and keep the information in context the same.

**Baselines**

We reuse Claim 1’s setup: the same Qwen3 models, Best-of-N with the same number of attempts as the no-learning baseline, and the paper’s wording as the reference condition

**Test instances**

- Game of 24: the paper’s 100 problems
- Creative writing: the paper’s 100 problems from the Tree of Thoughts dataset 

**Evaluation protocol**

- **Game of 24:** after each attempt, every step gets a 0–3 score, either from the model itself or from an exact oracle. We report problems solved per round, problems solved at least once so far, the gain over Best-of-N, and the format failure rate.
- **Creative writing:** a separate local model scores each passage for coherence from 1 to 10, using the paper’s grading prompt. That score is also our metric, replacing the paper’s AlpacaEval, which needs API access.