"""055 follow-up: the registry audit is key-free and honest about failures."""

from __future__ import annotations

from swarm import provider_audit


def test_the_audit_walks_every_provider_that_has_a_probe_url():
    seen: list[str] = []

    def status(url: str):
        seen.append(url)
        return 200, ""

    rows = provider_audit.audit(status=status, env={})
    assert len(rows) == len([p for p in provider_audit.providers.PROVIDERS if p.prefixes])
    assert seen, "the audit made no probes"


def test_a_wrong_base_fails_the_audit():
    rows = provider_audit.audit(
        ("openai",), status=lambda url: (404, ""), env={}
    )
    assert rows == [("openai", "wrong-base", "404 at https://api.openai.com/v1/models")]


def test_auth_required_is_healthy():
    rows = provider_audit.audit(("anthropic",), status=lambda url: (401, ""), env={})
    assert rows[0][1] == "auth-required"


def test_the_cli_exit_code_follows_wrong_base(monkeypatch, capsys):
    monkeypatch.setattr(
        provider_audit, "audit", lambda only: [("openai", "wrong-base", "404")]
    )
    assert provider_audit.main(["--only", "openai"]) == 1
    out = capsys.readouterr().out
    assert "openai" in out and "wrong-base" in out


def test_the_cli_is_clean_when_everything_answers(monkeypatch):
    monkeypatch.setattr(
        provider_audit, "audit", lambda only: [("openai", "auth-required", "")]
    )
    assert provider_audit.main([]) == 0
