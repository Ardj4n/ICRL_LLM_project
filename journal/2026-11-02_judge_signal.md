# Raw prompts: the judge's scores are mostly not real

From 2026-11-02: 800 judge responses of the raw smoke test.

- 94% hit `max_tokens`. The prompts have no chat template, and the judge prompt has no `/no_think`, so it reasons until cut off.
- 54.6% contain no `**Answer**`: the authors' parser gives them 0, the same as "impossible".
- 24.9% have one score in the first 300 characters, partly the model echoing the format example; the parser takes the first match.
- Only 13.2% end with a score.
- Mean judge return: 7.1 for empty answers (n=129), 3.8 for real answers (n=71).
- Policy: 129 of 200 answers are empty; 99% hit `max_tokens`.
- `generated_text` and `answer` are empty in the saved outputs (overwritten before saving), so raw policy text is lost.
- Not tested on 32B or 14B: unknown whether this is specific to 8B-AWQ.
