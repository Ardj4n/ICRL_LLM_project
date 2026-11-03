# Pilot tools added

- Wrapper options: `--prompt-format`, `--judge-thinking`, `--judge-max-tokens`, `--method best-of-n`, `--label`.
- `pilot/judge_quality.py` compares runs: cost, cuts, judge against the oracle.
- Prompts and responses: `ignored/game24/<model>_<label>/round_xxx/prompt_yyy.md`, one file per problem. A new run of the same variant replaces the folder.
- Everything runs from the Windows repo through `/mnt/c`: venv and tree-of-thought-llm in `~/icrl_deps`, models in `ignored/models/<name>`, passed by absolute path. Changes are uncommitted.
- The crash at `--gpu-mem-util 0.95` has no record: the next run started in the same minute and took its folder. Hence `--label`.

```bash
PY=~/icrl_deps/venv/bin/python
hf download Qwen/Qwen3-8B-AWQ --local-dir ignored/models/qwen3-8b-awq
$PY pilot/run_game24_pilot.py --model $PWD/ignored/models/qwen3-8b-awq --tot-path ~/icrl_deps/tree-of-thought-llm/src --gpu-mem-util 0.90 --max-model-len 24000 --prompt-format chat --label chat --rounds 3
$PY pilot/judge_quality.py pilot/results/<run_id> [more runs]
```
