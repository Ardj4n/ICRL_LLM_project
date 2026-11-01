**Model.** All experiments use Qwen3-32B (Qwen/Qwen3-32B, bf16, thinking mode disabled, served with vLLM on Renku) as both the policy and the self-judge, since it is the default open model in the authors’ implementation; if it does not fit our Renku GPU allocation, we use Qwen3-14B instead, decided after the pilot run and applied to all experiments.

**Claim 2: What ICRL Uses From Its History**

What the project is about:

1. **Ablation.** In ICRL, the model sees its previous attempts and their rewards in the prompt. **We test which parts of this history matter:**
   - Context size: how many previous attempts are kept.
   - Rewards: removed completely, instead of set to zero as in the paper (in the paper’s code, per-step rewards stay visible).
   - Order: whether the order of previous attempts matters.
   - Exploration: instead of always alternating explore and exploit, the model explores more when few attempts are available and exploits more as the history grows (epsilon-greedy).
2. **Generalization.** We use Qwen3-32B instead of GPT-4.1.
3. **Baselines**
    Reference: the paper’s setup (full history, rewards shown, attempts in order, alternating explore/exploit). Each condition changes one thing:
   - k = 3 (paper’s ablation) and k = 0 (no history, like Best-of-N).
   - Rewards removed.
   - Attempts in random order, or sorted by reward.
   - Epsilon-greedy exploration, with epsilon decreasing as more attempts are available.
4. **Evaluation protocol**
   Per-round and running-max success rate, as in the paper, and tokens used for the context-size conditions. Mean and standard error over 3 seeds, same problems and rounds for all conditions.
5. **Theorem/proof targets**
   Not applicable.
6. **Test instances**
   The paper’s 100 Game of 24 problems (indices 900–999 in the authors’ code).
7. **Compute budget**
   Authors’ code with vLLM. 7 conditions × 3 seeds = 21 runs, of which the reference and k = 0 runs (6) are shared with Claim 1, so 15 new runs. Rounds fixed after the pilot run.
8. **Expected limitations**
   We use one model and one task, so we compare trends, not the paper’s exact numbers.

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