"""Record what the machine offers, into a JSON file meant to be committed to git.

Standard library only, so it can run before the environment is installed.
Environment variables are read from an allowlist only: Renku sessions can hold
tokens in the environment and this file ends up in git.
"""
import argparse
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_ALLOWLIST = [
    "CUDA_VISIBLE_DEVICES",
    "NVIDIA_VISIBLE_DEVICES",
    "HF_HOME",
    "HF_HUB_CACHE",
    "OMP_NUM_THREADS",
]
PACKAGES = ["torch", "vllm", "transformers", "datasets", "numpy", "sympy", "openai"]
MODELS = ["Qwen/Qwen3-32B", "Qwen/Qwen3-14B"]
NETWORK_TEST_BYTES = 200 * 1024 * 1024


def run(cmd, timeout=60):
    """Return stdout, or None if the command is missing or fails."""
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def read_text(path):
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def to_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def gpu_info():
    fields = ["index", "name", "memory.total", "memory.used", "driver_version", "mig.mode.current"]
    out = run(["nvidia-smi", f"--query-gpu={','.join(fields)}", "--format=csv,noheader,nounits"])
    if out is None:
        return {"available": False, "count": 0, "gpus": []}
    gpus = []
    for line in out.splitlines():
        row = dict(zip(fields, (part.strip() for part in line.split(","))))
        gpus.append({
            "index": int(row["index"]),
            "name": row["name"],
            "memory_total_mib": to_number(row["memory.total"]),
            "memory_used_at_probe_mib": to_number(row["memory.used"]),
            "driver": row["driver_version"],
            "mig_mode": row["mig.mode.current"],
        })
    header = run(["nvidia-smi"]) or ""
    match = re.search(r"CUDA Version:\s*([\d.]+)", header)
    return {
        "available": True,
        "count": len(gpus),
        "cuda_driver_max": match.group(1) if match else None,
        # MIG setups can report [N/A] here.
        "total_memory_mib": sum(g["memory_total_mib"] for g in gpus if isinstance(g["memory_total_mib"], float)),
        "gpus": gpus,
    }


def torch_view():
    """Ask torch from a subprocess, so the caller never initialises CUDA itself."""
    code = (
        "import json, torch;"
        "print(json.dumps({'cuda_build': torch.version.cuda,"
        "'cuda_available': torch.cuda.is_available(),"
        "'device_count': torch.cuda.device_count(),"
        "'bf16_supported': torch.cuda.is_available() and torch.cuda.is_bf16_supported()}))"
    )
    out = run([sys.executable, "-c", code], timeout=180)
    if out is None:
        return None
    return json.loads(out.splitlines()[-1])


def cpu_info():
    model = None
    for line in (read_text("/proc/cpuinfo") or "").splitlines():
        if line.startswith("model name"):
            model = line.split(":", 1)[1].strip()
            break
    try:
        affinity = len(os.sched_getaffinity(0))
    except AttributeError:
        affinity = None
    # A container sees all the host's cores: the cgroup quota is the real limit.
    limit = None
    cpu_max = read_text("/sys/fs/cgroup/cpu.max")
    if cpu_max and not cpu_max.startswith("max"):
        quota, period = cpu_max.split()
        limit = int(quota) / int(period)
    else:
        quota = read_text("/sys/fs/cgroup/cpu/cpu.cfs_quota_us")
        period = read_text("/sys/fs/cgroup/cpu/cpu.cfs_period_us")
        if quota and period and int(quota) > 0:
            limit = int(quota) / int(period)
    return {
        "model": model,
        "host_visible_cores": os.cpu_count(),
        "affinity_cores": affinity,
        "cgroup_core_limit": limit,
    }


def memory_info():
    meminfo = {}
    for line in (read_text("/proc/meminfo") or "").splitlines():
        key, _, value = line.partition(":")
        meminfo[key] = value.strip()

    def to_gb(field):
        value = meminfo.get(field)
        return round(int(value.split()[0]) / 1024 ** 2, 2) if value else None

    limit = read_text("/sys/fs/cgroup/memory.max") or read_text("/sys/fs/cgroup/memory/memory.limit_in_bytes")
    limit_gb = None
    if limit and limit != "max":
        limit_gb = round(int(limit) / 1024 ** 3, 2)
    shm = shutil.disk_usage("/dev/shm").total / 1024 ** 3 if Path("/dev/shm").exists() else None
    return {
        "host_total_gb": to_gb("MemTotal"),
        "host_available_gb": to_gb("MemAvailable"),
        "cgroup_limit_gb": limit_gb,
        "shm_gb": round(shm, 2) if shm is not None else None,
    }


def filesystem_of(path):
    """Return the mount holding `path`, to tell a session disk from a data connector."""
    best = (None, None)
    for line in (read_text("/proc/mounts") or "").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        mount = parts[1]
        inside = str(path) == mount or str(path).startswith(mount.rstrip("/") + "/")
        if inside and (best[0] is None or len(mount) > len(best[0])):
            best = (mount, parts[2])
    return {"mount": best[0], "fstype": best[1]}


def write_speed_mb_s(directory, size_mb):
    target = Path(directory) / ".pilot_disk_test"
    block = os.urandom(1024 * 1024)
    start = time.monotonic()
    try:
        with open(target, "wb") as f:
            for _ in range(size_mb):
                f.write(block)
            f.flush()
            os.fsync(f.fileno())
        return round(size_mb / (time.monotonic() - start), 1)
    except OSError:
        return None
    finally:
        target.unlink(missing_ok=True)


def disk_info(paths, test_mb):
    result = {}
    for label, path in paths.items():
        path = Path(path)
        existing = path
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        usage = shutil.disk_usage(existing)
        result[label] = {
            "path": str(path),
            "free_gb": round(usage.free / 1e9, 1),
            "total_gb": round(usage.total / 1e9, 1),
            **filesystem_of(existing.resolve()),
            "write_mb_s": write_speed_mb_s(existing, test_mb) if test_mb else None,
        }
    return result


def hf_cache_dir():
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"])
    home = os.environ.get("HF_HOME")
    return Path(home) / "hub" if home else Path.home() / ".cache" / "huggingface" / "hub"


def model_info(repo, free_gb, cache_dir):
    info = {"repo": repo, "cached": (cache_dir / f"models--{repo.replace('/', '--')}").exists()}
    try:
        url = f"https://huggingface.co/api/models/{repo}/revision/main?blobs=true"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = json.load(response)
    except Exception as exc:
        info["error"] = f"{type(exc).__name__}: {exc}"
        return info
    siblings = data["siblings"]
    weights = sum(s.get("size") or 0 for s in siblings if s["rfilename"].endswith(".safetensors"))
    total = sum(s.get("size") or 0 for s in siblings)
    info.update(
        revision=data.get("sha"),
        download_gb=round(total / 1e9, 1),
        weights_gb=round(weights / 1e9, 1),
        fits_on_cache_disk=total / 1e9 < free_gb,
    )
    shards = [s["rfilename"] for s in siblings if s["rfilename"].endswith(".safetensors")]
    info["_sample_file"] = shards[0] if shards else None
    return info


def download_speed_mb_s(repo, filename):
    """Time a partial download, without saving it, to estimate the model download time."""
    url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
    request = urllib.request.Request(url, headers={"Range": f"bytes=0-{NETWORK_TEST_BYTES - 1}"})
    received = 0
    start = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                received += len(chunk)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {"mb_s": round(received / 1e6 / (time.monotonic() - start), 1), "bytes_read": received}


def git_info():
    def git(*args):
        return run(["git", "-C", str(ROOT), *args])

    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
    }


def package_versions():
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def collect(disk_test_mb=1024, query_network=True, manual=None, extra_disks=None):
    cache_dir = hf_cache_dir()
    disks = {"project": ROOT, "hf_cache": cache_dir, "tmp": "/tmp"}
    disks.update(extra_disks or {})
    disk = disk_info(disks, disk_test_mb)
    report = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manual": manual or {},
        "gpu": gpu_info(),
        "torch": torch_view(),
        "cpu": cpu_info(),
        "memory": memory_info(),
        "disk": disk,
        "os": {"platform": platform.platform(), "python": platform.python_version()},
        "packages": package_versions(),
        "git": git_info(),
        "env": {name: os.environ[name] for name in ENV_ALLOWLIST if name in os.environ},
    }
    if query_network:
        models = [model_info(repo, disk["hf_cache"]["free_gb"], cache_dir) for repo in MODELS]
        sample = next((m for m in models if m.get("_sample_file")), None)
        report["network_to_huggingface"] = (
            download_speed_mb_s(sample["repo"], sample["_sample_file"]) if sample else None
        )
        for m in models:
            m.pop("_sample_file", None)
        report["models"] = models
    return report


def gpu_slug(report):
    gpu = report["gpu"]
    if not gpu["gpus"]:
        return "nogpu"
    name = gpu["gpus"][0]["name"].replace("NVIDIA", "").strip().lower()
    return f"{gpu['count']}x{re.sub(r'[^a-z0-9]+', '-', name).strip('-')}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="default: pilot/results/<date>_<gpu>_probe/system.json")
    parser.add_argument("--resource-class", default=None, help="Renku resource class name, from the UI")
    parser.add_argument("--idle-timeout", default=None, help="pool's auto-pause timer, from the UI")
    parser.add_argument("--quota-notes", default=None, help="pool quota, GPU hours granted, anything else")
    parser.add_argument("--disk-test-mb", type=int, default=1024, help="0 skips the write test")
    parser.add_argument("--no-network", action="store_true", help="skip Hugging Face queries")
    parser.add_argument("--disk", action="append", default=[], metavar="LABEL=PATH", help="extra disk to test")
    args = parser.parse_args()

    manual = {
        "resource_class": args.resource_class,
        "idle_timeout": args.idle_timeout,
        "quota_notes": args.quota_notes,
    }
    extra = dict(item.split("=", 1) for item in args.disk)
    report = collect(args.disk_test_mb, not args.no_network, manual, extra)

    out = args.out
    if out is None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M")
        out = ROOT / "pilot" / "results" / f"{stamp}_{gpu_slug(report)}_probe" / "system.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print(f"\nSaved to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
