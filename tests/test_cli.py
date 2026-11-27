

def test_report_forwards_the_manual_gate(monkeypatch):
    from swarm import cli

    calls: list[tuple[str, list[str]]] = []

    def fake_forward(module: str, args: list[str], *, target=None) -> int:
        calls.append((module, list(args)))
        return 1

    monkeypatch.setattr(cli, "_forward", fake_forward)
    assert cli.main(["report", "--fail-on-manual"]) == 1
    assert calls == [("swarm.report", ["--fail-on-manual"])]
