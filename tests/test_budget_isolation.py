"""A per-task budget cap must not leak its delta into the next task (059 AC-2)."""

from __future__ import annotations

from types import SimpleNamespace

from swarm.flow import _discard_partial_task


class _Flow:
    def __init__(self) -> None:
        self.state = SimpleNamespace(changed_files=["frontend/src/App.svelte", "new.ts"])
        self.calls: list[tuple[list[str], str]] = []

    def _revert_paths(self, paths: list[str], *, reason: str = "paths") -> list[str]:
        self.calls.append((list(paths), reason))
        return list(paths)


def test_a_capped_task_delta_is_reverted() -> None:
    flow = _Flow()
    assert _discard_partial_task(flow) == ["frontend/src/App.svelte", "new.ts"]
    assert flow.calls == [(["frontend/src/App.svelte", "new.ts"], "task cap")]


def test_no_delta_is_a_noop() -> None:
    flow = _Flow()
    flow.state.changed_files = []
    assert _discard_partial_task(flow) == []
    assert flow.calls == []
