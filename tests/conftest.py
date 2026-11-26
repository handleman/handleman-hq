"""Test defaults: clean checkouts have no `.env`, so provide non-secret placeholder models.

Real `.env` values (when present) always win; this only fills the gaps so tests
that build CrewAI LLM objects do not depend on a developer machine's keys.
"""

import os

import pytest

_MODEL_DEFAULTS = {
    "SWARM_PLANNER_MODEL": "ollama/qwen3.5:9b",
    "SWARM_CODER_MODEL": "ollama/swarm-coder:latest",
    "SWARM_REVIEWER_MODEL": "ollama/swarm-qa:latest",
    "SWARM_SENIOR_MODEL": "ollama/qwen3.5:9b",
    "OLLAMA_BASE_URL": "http://localhost:11434",
    "SWARM_ALLOW_PAID": "0",
}
_KEY_DEFAULTS = {
    "OPENROUTER_API_KEY": "test-openrouter-key",
    "OPENCODE_API_KEY": "test-opencode-key",
}


@pytest.fixture(autouse=True)
def _default_swarm_env(monkeypatch):
    for key, value in {**_MODEL_DEFAULTS, **_KEY_DEFAULTS}.items():
        if not os.environ.get(key):
            monkeypatch.setenv(key, value)


_SPEC_MD = """# 020 harness efficiency

- **AC-2 — cache hints.** Prompt cache hints lower the cost of every step.
- **AC-3 — prompt size.** The prefix stays byte-identical across steps.
"""

_PLAN_MD = """# Plan

STEP 1: add `swarm/bench/corpus.py` with the replay cases.
STEP 2: wire the corpus into the bench entry point.
"""

_TASKS_MD = """# Tasks

- [x] T1 (AC-1): Add `swarm/bench/corpus.py`.
- [ ] T2 (AC-2, AC-3): Keep the prompt prefix stable.
"""


@pytest.fixture
def spec_repo(tmp_path, monkeypatch):
    """A repo root with product specs, for name/AC/plan resolution.

    The factory ships no `specs/product/` (those stay in the app repo), so tests
    that resolve a spec directory or read its AC/plan text need a fixture root.
    """
    root = tmp_path / "repo"
    for name in ("001-example-app", "020-harness-efficiency"):
        spec = root / "specs" / "product" / name
        spec.mkdir(parents=True)
        (spec / "spec.md").write_text(_SPEC_MD)
        (spec / "plan.md").write_text(_PLAN_MD)
        (spec / "tasks.md").write_text(_TASKS_MD)
    from swarm import flow, prompts

    monkeypatch.setattr(prompts, "REPO_ROOT", root, raising=False)
    monkeypatch.setattr(flow, "REPO_ROOT", root, raising=False)
    return root
