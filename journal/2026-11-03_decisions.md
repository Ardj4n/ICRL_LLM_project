# Decisions

| # | Decision | Options | Recommendation |
| --- | --- | --- | --- |
| 1 | Model | 32B, 14B, 8B-AWQ | By VRAM: 32B from ~100 GB, 14B from 40 GB, 8B-AWQ on 12 GB |
| 2 | Model good enough? | Keep or change | Must beat Best-of-N in the pilot |
| 3 | Rounds | 30-50 | Fewest that show the trend |
| 4 | More compute? | Renku or more | After the pilot: hours × runs vs quota |
| 5 | Runs in scope | Claim 2 = 21 runs (15 new), plus Claims 1 and 3 | Agree on one final list |
| 6 | Success metric | Authors' or strict | Report both, pick after the pilot |
| 7 | Raw outputs | Session disk or data connector | Connector for real runs |
| 8 | Checkpoint resume | Implement or not | Needed if a run outlasts a session |
| 9 | Changing authors' code | Wrapper or edits | Wrapper: `sync_authors.py` overwrites `authors/` |
| 10 | Prompt format | Raw or chat template | Chat: raw gives no usable judge. Declare it in the report |
| 11 | Judge token limit | 1024 or more | After the judge-thinking run: most cuts fall on unreachable steps |
