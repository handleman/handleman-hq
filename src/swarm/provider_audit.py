"""`make provider-audit` — probe the whole registry without a key (055 follow-up).

The registry drifts as providers add/rename endpoints. This walks every provider,
runs the key-free reachability probe, and reports a table. It never sends a key
and never needs an account.

    python -m swarm.provider_audit [--only openai,anthropic] [--timeout 6]

Exit codes: 0 every provider answered in an expected way, 1 at least one is
`wrong-base` (a URL we ship is stale) or `unreachable` (network/registry issue).
`auth-required` and `reachable` are healthy; `incident` is the provider's fault
and is reported but does not fail the audit.
"""

from __future__ import annotations

import argparse
import os

from swarm import preflight, providers


def audit(
    only: tuple[str, ...] = (),
    *,
    status=preflight._http_status,
    env: dict[str, str] | None = None,
) -> list[tuple[str, str, str]]:
    source = os.environ if env is None else env
    rows: list[tuple[str, str, str]] = []
    for provider in providers.PROVIDERS:
        if only and provider.name not in only:
            continue
        verdict, detail = preflight.probe_provider(provider.name, dict(source), status=status)
        rows.append((provider.name, verdict, detail))
    return rows


def _is_fatal(name: str, verdict: str) -> bool:
    """Local providers are optional; their absence is not registry drift."""
    if verdict not in {"wrong-base", "unreachable"}:
        return False
    provider = providers.by_name(name)
    return not (provider and provider.kind == "local")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="provider-audit", description=__doc__)
    parser.add_argument("--only", default="", help="comma-separated provider names")
    parser.add_argument("--timeout", type=float, default=6.0)
    args = parser.parse_args(argv)
    only = tuple(part.strip() for part in args.only.split(",") if part.strip())
    rows = audit(only)
    width = max((len(name) for name, _, _ in rows), default=8)
    fail = 0
    for name, verdict, detail in rows:
        print(f"{name:<{width}}  {verdict:<14} {detail}")
        if _is_fatal(name, verdict):
            fail = 1
    print(
        f"provider-audit: {len(rows)} provider(s), "
        f"{sum(1 for name, v, _ in rows if _is_fatal(name, v))} problem(s)"
    )
    return fail


if __name__ == "__main__":
    raise SystemExit(main())
