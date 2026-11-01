#!/usr/bin/env bash
# Prepare a Renku session for the pilot. Safe to run again after a session restart.
#   export HF_HOME=/path/on/a/large/disk   # Qwen3-32B is a 66 GB download
#   bash pilot/setup_renku.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$ROOT/pilot/runs/_deps/venv"
TOT="$ROOT/pilot/runs/_deps/tree-of-thought-llm"
TOT_COMMIT=8050e67d0e3a0fddc424d7fa5801538722a4c4cc

if ! command -v uv >/dev/null; then
    python3 -m pip install --user uv
    export PATH="$HOME/.local/bin:$PATH"
fi

# Python 3.11 as in the authors' README; the project's 3.12 is not used here.
uv venv --python 3.11 --allow-existing "$VENV"
uv pip install --python "$VENV/bin/python" -r "$ROOT/pilot/requirements.lock.txt"

if [ ! -d "$TOT" ]; then
    git clone https://github.com/princeton-nlp/tree-of-thought-llm "$TOT"
fi
git -C "$TOT" checkout --quiet "$TOT_COMMIT"

command -v tmux >/dev/null || echo "WARNING: tmux not found. Long runs need nohup instead."
[ -n "${HF_HOME:-}" ] || echo "WARNING: HF_HOME not set. The model will go to ~/.cache/huggingface."

echo
echo "Ready. Use: $VENV/bin/python pilot/probe_system.py"
