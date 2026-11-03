# Why outputs are cut

From 2026-11-03.

The limits are the authors': 1000 tokens for the policy, 1024 for the judge.

- Raw: without a template the model does not stop by itself (94-99% cut). Its text was not saved, so there are no examples.
- Chat, policy: never cut (0 of 600).
- Chat, judge: thinking off only removes the `<think>` block. The judge still reasons in the open, with the score last, so a cut almost always means no score, which the parser turns into 0 (240 of 242 cuts).
- It searches for a way to reach 24, and stops when it finds one. So it is cut when there is nothing to find: 8B cuts 1.4% of reachable steps and 6.0% of unreachable ones (45 of 47 cuts on real attempts are unreachable, where 0 is right). 4B: 6.7% and 8.3%.
- More numbers left means a longer search. 8B on real attempts: first step 10.4%, second 4.0%, third 1.3%, solution 0%.
- Often it repeats itself until the limit: 21 of 48 cuts for 8B, 157 of 194 for 4B.
- 4B: 147 of its 194 cuts come from empty attempts. On real attempts it is close to 8B (6.1% against 3.9%).
- Empty attempts: the model writes a normal response without `<answer>` tags (all 106), the authors' regex returns nothing, and the judge must score a blank step (first step cut 69%, against 10%). They jump after round 0 (1, 58, 47). Likely cause, not tested: it imitates the history, which shows attempts without tags. One 8B response copies even the `<Reward:` tags.

Examples, cut from `ignored/` into `pilot/chats/`, each with its source:

- Long search: [8B](../pilot/chats/judge_long_search_8b.md)
- Repeating: [8B](../pilot/chats/judge_repeating_8b.md), [4B](../pilot/chats/judge_repeating_4b.md)
- Blank step: [4B policy without tags](../pilot/chats/policy_no_tags_4b.md), [its judge](../pilot/chats/judge_blank_step_4b.md)
- Cut after the score, harmless: [4B](../pilot/chats/judge_cut_after_score_4b.md)
- Tags imitated: [8B](../pilot/chats/policy_imitates_reward_tags_8b.md)
- Right steps, wrong expression: [4B](../pilot/chats/policy_wrong_expression_4b.md)
- Rewards in the history: [8B](../pilot/chats/policy_history_8b.md)
