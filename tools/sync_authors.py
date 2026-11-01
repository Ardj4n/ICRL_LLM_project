"""Copy the authors' code into authors/ from a git tag, removing API keys.

The upstream repository is cloned into ignored/, which git does not track, and
authors/ is rebuilt from the tag. Upstream has hard-coded keys, so every text file
is scrubbed, and nothing is replaced unless a second scan finds no key left.
Keys are never printed.

    python tools/sync_authors.py --dry-run
    python tools/sync_authors.py
    python tools/sync_authors.py --tag some-other-tag
"""
import argparse
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "authors"
IGNORED = ROOT / "ignored"
CLONE = IGNORED / "ICRL-for-LLM-Agent"
UPSTREAM_URL = "https://github.com/garified/ICRL-for-LLM-Agent"

# Upstream's only tag is too old, so this one is created in the local clone.
DEFAULT_TAG = "icrl-proposal-base"
DEFAULT_TAG_COMMIT = "43429cdcf790c61aeebbcefa9fe8a83bd7fe24b6"

EXCLUDED = {".gitignore"}  # the root .gitignore applies instead
PLACEHOLDER = b"YOUR_API_KEY"
PROVENANCE_FILE = "UPSTREAM.json"

# Whole matches that are always keys.
KEY_FORMATS = {
    "openai_style": rb"sk-[A-Za-z0-9_-]{20,}",
    "huggingface": rb"hf_[A-Za-z0-9]{30,}",
    "github": rb"(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_\w{20,})",
    "google": rb"AIza[0-9A-Za-z_-]{35}",
    "aws": rb"AKIA[0-9A-Z]{16}",
    "slack": rb"xox[baprs]-[A-Za-z0-9-]{10,}",
}
# Quoted values next to a name that says they are secret. Group 1 is the value.
QUOTED_VALUES = {
    "api_key_assignment": rb"(?i:api[_-]?key|api[_-]?token|secret[_-]?key|auth[_-]?token)"
                          rb"[\"']?\s*[=:]\s*[\"']([^\"'\s]{16,})[\"']",
    "getenv_default": rb"(?:KEY|TOKEN|SECRET)[\"']\s*,\s*[\"']([^\"'\s]{16,})[\"']",
}
NOT_A_KEY = re.compile(rb"(?i)your|placeholder|example|xxxx")


def git(*args, cwd=None, binary=False):
    # autocrlf off, so that files come out byte for byte as upstream committed them.
    result = subprocess.run(
        ["git", "-c", "core.autocrlf=false", *args],
        cwd=cwd, capture_output=True, check=False,
    )
    if result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stderr.decode(errors='replace')}")
    return result.stdout if binary else result.stdout.decode().strip()


def ensure_clone():
    IGNORED.mkdir(exist_ok=True)
    if not (CLONE / ".git").exists():
        print(f"Cloning {UPSTREAM_URL} into {CLONE.relative_to(ROOT).as_posix()}")
        git("clone", "--quiet", UPSTREAM_URL, str(CLONE))
    else:
        url = git("remote", "get-url", "origin", cwd=CLONE)
        if url.rstrip("/").removesuffix(".git") != UPSTREAM_URL:
            sys.exit(f"{CLONE} points to {url}, not {UPSTREAM_URL}")
        git("fetch", "--quiet", "--tags", "origin", cwd=CLONE)


def commit_of(tag):
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}^{{commit}}"],
        cwd=CLONE, capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def resolve_tag(tag):
    """Return the tag's commit, creating the default tag if needed."""
    commit = commit_of(tag)
    if tag == DEFAULT_TAG:
        if commit is None:
            git("tag", DEFAULT_TAG, DEFAULT_TAG_COMMIT, cwd=CLONE)
            commit = commit_of(tag)
        if commit != DEFAULT_TAG_COMMIT:
            sys.exit(f"Tag {tag} points to {commit}, expected {DEFAULT_TAG_COMMIT}")
    if commit is None:
        sys.exit(f"Tag {tag} not found. To add one: git -C {CLONE.as_posix()} tag {tag} <commit>")
    return commit


def export_tag(tag, destination):
    archive = git("archive", "--format=tar", f"refs/tags/{tag}", cwd=CLONE, binary=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for member in tar.getmembers():
            if not (member.isfile() or member.isdir()):
                continue
            path = destination / member.name
            if destination.resolve() not in path.resolve().parents and path.resolve() != destination.resolve():
                sys.exit(f"Unsafe path in the archive: {member.name}")
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.name not in EXCLUDED:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tar.extractfile(member).read())


def is_binary(data):
    return b"\0" in data[:8192]


def scrub_bytes(data):
    """Return the scrubbed data and how many values each rule replaced."""
    counts = {}

    def count(kind):
        counts[kind] = counts.get(kind, 0) + 1

    for kind, pattern in KEY_FORMATS.items():
        def replace_key(_, kind=kind):
            count(kind)
            return PLACEHOLDER

        data = re.sub(pattern, replace_key, data)

    for kind, pattern in QUOTED_VALUES.items():
        def replace_value(match, kind=kind):
            value = match.group(1)
            if NOT_A_KEY.search(value):
                return match.group(0)
            count(kind)
            start, end = match.span(1)
            offset = match.start(0)
            whole = match.group(0)
            return whole[:start - offset] + PLACEHOLDER + whole[end - offset:]

        data = re.sub(pattern, replace_value, data)
    return data, counts


def scrub_tree(directory):
    """Scrub every text file. Fail if a second scan still finds something."""
    scrubbed = []
    for path in sorted(p for p in directory.rglob("*") if p.is_file()):
        data = path.read_bytes()
        if is_binary(data):
            continue
        clean, counts = scrub_bytes(data)
        if counts:
            path.write_bytes(clean)
            scrubbed.append({"file": path.relative_to(directory).as_posix(), "replaced": counts})

    leftovers = []
    for path in directory.rglob("*"):
        if path.is_file() and not is_binary(path.read_bytes()) and scrub_bytes(path.read_bytes())[1]:
            leftovers.append(path.relative_to(directory).as_posix())
    if leftovers:
        sys.exit(f"Keys still found after scrubbing, nothing replaced: {leftovers}")
    return scrubbed


def uncommitted_changes():
    """Tracked or new files in authors/ that replacing it would lose. Ignored files are expendable."""
    return git("status", "--porcelain", "--", TARGET.name, cwd=ROOT)


def tree_files(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


def normalized(data):
    return data.replace(b"\r\n", b"\n")


def report_differences(new, old):
    new_files, old_files = tree_files(new), tree_files(old)
    added = sorted(set(new_files) - set(old_files))
    removed = sorted(set(old_files) - set(new_files))
    changed = sorted(
        f for f in set(new_files) & set(old_files)
        if normalized(new_files[f]) != normalized(old_files[f])
    )
    print(f"Compared with the current authors/: {len(added)} added, {len(removed)} removed, {len(changed)} changed")
    for label, files in (("added", added), ("removed", removed), ("changed", changed)):
        for name in files:
            print(f"  {label}: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tag", default=DEFAULT_TAG, help=f"tag in the clone (default: {DEFAULT_TAG})")
    parser.add_argument("--dry-run", action="store_true", help="show the result without touching authors/")
    parser.add_argument("--force", action="store_true", help="replace authors/ even with uncommitted changes")
    args = parser.parse_args()

    ensure_clone()
    commit = resolve_tag(args.tag)
    git("checkout", "--quiet", "--detach", f"refs/tags/{args.tag}", cwd=CLONE)
    print(f"Tag {args.tag} -> {commit}")

    # Stays on the same disk as authors/, so that the final move is a rename.
    with tempfile.TemporaryDirectory(dir=IGNORED, prefix="sync_") as temp:
        staged = Path(temp) / "authors"
        staged.mkdir()
        export_tag(args.tag, staged)
        scrubbed = scrub_tree(staged)
        provenance = {"repository": UPSTREAM_URL, "tag": args.tag, "commit": commit, "scrubbed": scrubbed}
        (staged / PROVENANCE_FILE).write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")

        print(f"Scrubbed {sum(sum(s['replaced'].values()) for s in scrubbed)} value(s) in {len(scrubbed)} file(s):")
        for item in scrubbed:
            print(f"  {item['file']}: {item['replaced']}")
        if TARGET.exists():
            report_differences(staged, TARGET)

        if args.dry_run:
            print("Dry run: authors/ not touched.")
            return
        changes = uncommitted_changes()
        if changes and not args.force:
            sys.exit(f"authors/ has uncommitted changes, which would be lost. Use --force to replace it:\n{changes}")
        if TARGET.exists():
            shutil.rmtree(TARGET)
        shutil.move(str(staged), str(TARGET))
    print("authors/ updated. Check it with: git status authors && git diff authors")


if __name__ == "__main__":
    main()
