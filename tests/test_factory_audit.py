"""054 AC-5: a pre-push audit catches what the subdirectory filter drops."""

from __future__ import annotations

import subprocess
from pathlib import Path

from swarm import factory_audit


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / ".gitignore").write_text("__pycache__/\n.venv/\n.env\n")
    (root / ".dockerignore").write_text(".env\n")
    (root / "README.md").write_text("# x\n")
    (root / "pyproject.toml").write_text("[project]\nname='x'\n")
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "x"],
        cwd=root,
        check=True,
    )
    return root


def test_a_clean_repo_passes(tmp_path):
    root = _repo(tmp_path, {"src/x.py": "x = 1\n"})
    assert factory_audit.audit(root) == []


def test_pycache_is_never_published(tmp_path):
    """The 2026-11-26 filtered factory tracked 120 pycache files."""
    root = _repo(tmp_path, {"src/__pycache__/x.pyc": "x"})
    problems = factory_audit.audit(root)
    assert any("cache" in p and "__pycache__" in p for p in problems)


def test_a_tracked_env_file_blocks_the_push(tmp_path):
    root = _repo(tmp_path, {".env": "OPENROUTER_API_KEY=secret\n"})
    assert any("secret" in p or ".env" in p for p in factory_audit.audit(root))


def test_the_example_env_is_allowed(tmp_path):
    root = _repo(tmp_path, {".env.example": "SWARM_CODER_MODEL=\n"})
    assert factory_audit.audit(root) == []


def test_a_large_blob_blocks_the_push(tmp_path):
    root = _repo(tmp_path, {"data/big.bin": "x" * (factory_audit.MAX_BLOB + 10)})
    assert any("over 1 MB" in p for p in factory_audit.audit(root))


def test_a_missing_hygiene_file_is_reported(tmp_path):
    root = _repo(tmp_path, {"src/x.py": "x = 1\n"})
    (root / ".dockerignore").unlink()
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "rm"],
        cwd=root,
        check=True,
    )
    assert any(".dockerignore" in p for p in factory_audit.audit(root))


def test_an_uncovered_ignore_rule_is_reported(tmp_path):
    root = _repo(tmp_path, {"src/x.py": "x = 1\n"})
    (root / ".gitignore").write_text(".env\n")
    subprocess.run(["git", "add", "-A", "-f"], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "ig"],
        cwd=root,
        check=True,
    )
    assert any("does not cover __pycache__" in p for p in factory_audit.audit(root))


def test_a_non_repo_is_rejected(tmp_path):
    assert factory_audit.audit(tmp_path) == [f"{tmp_path} is not a git checkout"]


def test_main_exits_non_zero_on_problems(tmp_path):
    root = _repo(tmp_path, {"x/__pycache__/a.pyc": "x"})
    assert factory_audit.main(["--root", str(root)]) == 1


def test_this_factory_checkout_is_clean():
    """The factory itself must pass its own gate (run from the repo root)."""
    root = Path(__file__).resolve().parents[1]
    assert factory_audit.audit(root) == []
