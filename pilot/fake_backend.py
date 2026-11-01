"""Fake vLLM, ToT and heavy libraries for `run_game24_pilot.py --dry-run`.

Tests the measuring tool without a GPU. Only numpy and sympy must be real, since
the authors' code uses them to check answers. The numbers it produces mean nothing.
"""
import sys
import time
import types

GOOD = "(6 - 4) * (4 + 8) = 24"
BAD = "(6 + 4) * (4 + 8) = 24"
STEPS = "**Response** Step1: 4 + 8 = 12 (left: 4 6 12) Step2: 6 - 4 = 2 (left: 2 12) Step3: 2 * 12 = 24 (left: 24)"


class Completion:
    def __init__(self, text, finish_reason):
        self.text = text
        self.token_ids = text.split()
        self.finish_reason = finish_reason


class RequestOutput:
    def __init__(self, prompt, text, finish_reason):
        self.prompt_token_ids = prompt.split()
        self.outputs = [Completion(text, finish_reason)]


class Metric:
    def __init__(self, name, value):
        self.name = name
        self.value = value


class SamplingParams:
    def __init__(self, temperature=1.0, top_p=1.0, max_tokens=16):
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens


class LLM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.policy_calls = 0
        self.preemptions = 0

    def get_metrics(self):
        return [Metric("vllm:num_preemptions", self.preemptions), Metric("vllm:gpu_cache_usage_perc", 0.5)]

    def generate(self, prompts, sampling_params, use_tqdm=True):
        self.preemptions += 1
        outputs = []
        if sampling_params.temperature > 0:
            # Odd rounds solve the puzzle, so that the success curve can be checked.
            answer = GOOD if self.policy_calls % 2 else BAD
            self.policy_calls += 1
            text = f"<answer>{STEPS} **Answer**: {answer}</answer>"
            outputs = [RequestOutput(p, text, "length" if i < 10 else "stop") for i, p in enumerate(prompts)]
            # Time grows with the prompt, as with a real model.
            time.sleep(0.01 + sum(len(p) for p in prompts) * 1e-8)
        else:
            outputs = [RequestOutput(p, "**Answer**: 3.", "stop") for p in prompts]
            time.sleep(0.01)
        return outputs


class Task:
    def get_input(self, idx):
        return "4 4 6 8"


def module(name, **attributes):
    fake = types.ModuleType(name)
    fake.__dict__.update(attributes)
    sys.modules[name] = fake
    return fake


def install():
    module("vllm", LLM=LLM, SamplingParams=SamplingParams)
    module("transformers", AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda _: None))
    module("datasets", load_dataset=None)
    module("openai", OpenAI=None)
    module("tqdm")
    module("tot")
    module("tot.tasks", get_task=lambda _: Task())
    module("tot.prompts")
    module(
        "tot.prompts.game24",
        standard_prompt="", cot_prompt="", propose_prompt="", value_prompt="", value_last_step_prompt="",
    )
