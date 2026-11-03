# Pilot run 20261101-2327_1xgeforce-rtx-3060_qwen3-8b-awq_s0

- **Status:** crashed, 0 of 2 rounds complete
- **Model:** Qwen/Qwen3-8B-AWQ, seed 0
- **GPUs:** 1 × NVIDIA GeForce RTX 3060, 12 GiB in total
- **Total time:** 0.13 h; model load n/a s
- **Raw output size:** 0 MB for this run

## Crash

```
 "/home/ardj/ICRL_LLM_project/pilot/runs/_deps/venv/lib/python3.11/site-packages/vllm/v1/engine/llm_engine.py", line 103, in __init__
    self.engine_core = EngineCoreClient.make_client(
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ardj/ICRL_LLM_project/pilot/runs/_deps/venv/lib/python3.11/site-packages/vllm/v1/engine/core_client.py", line 77, in make_client
    return SyncMPClient(vllm_config, executor_class, log_stats)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/ardj/ICRL_LLM_project/pilot/runs/_deps/venv/lib/python3.11/site-packages/vllm/v1/engine/core_client.py", line 514, in __init__
    super().__init__(
  File "/home/ardj/ICRL_LLM_project/pilot/runs/_deps/venv/lib/python3.11/site-packages/vllm/v1/engine/core_client.py", line 408, in __init__
    with launch_core_engines(vllm_config, executor_class,
  File "/home/ardj/.local/share/uv/python/cpython-3.11.18-linux-x86_64-gnu/lib/python3.11/contextlib.py", line 144, in __exit__
    next(self.gen)
  File "/home/ardj/ICRL_LLM_project/pilot/runs/_deps/venv/lib/python3.11/site-packages/vllm/v1/engine/utils.py", line 697, in launch_core_engines
    wait_for_engine_startup(
  File "/home/ardj/ICRL_LLM_project/pilot/runs/_deps/venv/lib/python3.11/site-packages/vllm/v1/engine/utils.py", line 750, in wait_for_engine_startup
    raise RuntimeError("Engine core initialization failed. "
RuntimeError: Engine core initialization failed. See root cause above. Failed core proc(s): {}
```

## Cost by phase

| Phase | Total | s/round | gen tok/s | gen tokens/call | Hit max_tokens | Preemptions |
| --- | --- | --- | --- | --- | --- | --- |
| Policy | – | – | – | – | – | – |
| Judge | – | – | – | – | – | – |

## GPU during the run

| GPU | Samples | Mean util % | Peak memory (GiB) | Max power (W) | Max temp (°C) | Throttle codes |
| --- | --- | --- | --- | --- | --- | --- |
| 0.0 | 47 | 5 | 7.3 / 12 | 138.97 | 50.0 | 0x0000000000000001 ×45, 0x0000000000000000 ×2 |
