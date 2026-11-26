"""`hq design` / `hq figma` (057): sync, check, brief, verify, auth, status, logout."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from swarm import contract as contract_mod
from swarm.design import checks, oauth, sync
from swarm.design.config import DesignConfig, DesignConfigError, load_design
from swarm.design.mcp import DesignError
from swarm.design.rest import RestError
from swarm.paths import target_root


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="hq design", description=__doc__)
    area = parser.add_subparsers(dest="area", required=True)

    figma = area.add_parser("figma", help="Figma authorization and token status")
    action = figma.add_subparsers(dest="action", required=True)
    auth = action.add_parser("auth", help="authorize the MCP server (first run)")
    auth.add_argument("--no-open", action="store_true", help="do not open the browser")
    auth.add_argument("--non-interactive", action="store_true", help="print the URL and exit")
    auth.add_argument("--timeout", type=float, default=0, help="seconds to wait for the redirect")
    action.add_parser("status", help="token presence/expiry (never the token)")
    action.add_parser("logout", help="delete the stored token")

    design = area.add_parser("design", help="design cache and checks")
    action = design.add_subparsers(dest="action", required=True)
    for name, text in (
        ("sync", "fetch the configured frames into designs/"),
        ("check", "verify the cache and lock"),
        ("brief", "print the cached design brief"),
    ):
        child = action.add_parser(name, help=text)
        child.add_argument("--spec", default="", help="spec directory name")
        child.add_argument("--transport", default="", choices=["", "auto", "mcp", "rest"])
        if name == "sync":
            child.add_argument("--force", action="store_true", help="refetch even when current")
            child.add_argument("--no-open", action="store_true", help="do not open the browser")
            child.add_argument("--non-interactive", action="store_true", help="fail typed instead of waiting")
    verify = action.add_parser("verify", help="evaluate browser facts against design.toml")
    verify.add_argument("--spec", required=True, help="spec directory name")
    verify.add_argument("--facts", required=True, help="JSON: tokens/regions/screenshots")
    verify.add_argument("--root", default="", help="repo root for baseline paths")
    return parser


def _config(root: Path, spec: str) -> DesignConfig:
    current = contract_mod.current(root)
    mapping = current.design or None
    if mapping is None:
        raise DesignConfigError("swarm.yaml has no design: block")
    spec_dir = (root / current.specs_dir / spec) if spec else None
    config = load_design(root, spec_dir, mapping=mapping)
    if config is None:
        raise DesignConfigError("design block is empty")
    return config


def _non_interactive(args: argparse.Namespace) -> bool:
    return bool(getattr(args, "non_interactive", False)) or (
        os.environ.get("SWARM_NONINTERACTIVE", "").strip() in {"1", "true", "yes"}
    )


def _print_url(url: str) -> None:
    # `oauth` also prints; keep the stdout copy for the dashboard/log capture.
    print(f"figma: authorize at {url}", flush=True)


def _run(args: argparse.Namespace, root: Path) -> int:
    action = args.action
    if args.area == "figma":
        if action == "status" and not contract_mod.current(root).design:
            print(json.dumps({"configured": False}, indent=2, sort_keys=True))
            return 0
        config = _config(root, "")
        if action == "status":
            print(json.dumps(sync.status(config), indent=2, sort_keys=True))
            return 0
        if action == "logout":
            print("figma: token removed" if oauth.logout(config) else "figma: no token stored")
            return 0
        if action == "auth":
            try:
                status = oauth.authorize(
                    config,
                    open_browser=not args.no_open,
                    timeout=args.timeout or None,
                    on_url=_print_url,
                    non_interactive=args.non_interactive,
                )
            except oauth.FigmaAuthRequired as exc:
                print(f"figma_auth_required: {exc.url}")
                return 2
            print(json.dumps(status, indent=2, sort_keys=True))
            return 0
        return 1

    config = _config(root, args.spec)
    if action == "sync":
        try:
            result = sync.sync(
                root,
                config,
                force=args.force,
                transport=args.transport,
                on_url=_print_url,
                non_interactive=_non_interactive(args),
            )
        except oauth.FigmaAuthRequired as exc:
            print(f"figma_auth_required: {exc.url}")
            return 2
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    if action == "check":
        result = sync.check(root, config)
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0 if result.get("ok") else 1
    if action == "brief":
        text = sync.brief_for(root, config)
        print(text or "design: no cached brief — run `hq design sync`")
        return 0 if text else 1
    if action == "verify":
        spec_dir = root / contract_mod.current(root).specs_dir / args.spec
        table = checks.load_checks(spec_dir)
        if table is None:
            print(f"design: {spec_dir}/design.toml not found")
            return 1
        try:
            facts = json.loads(Path(args.facts).read_text())
        except (OSError, ValueError) as exc:
            print(f"design: unreadable facts: {exc}")
            return 1
        issues = checks.evaluate(table, facts, root=Path(args.root or root))
        for issue in issues:
            print(f"{issue['check']} {issue['target']}: {issue['detail']} [{issue['ac']}]")
        print(f"design verify: {len(issues)} issue(s)")
        return 1 if issues else 0
    return 1


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = target_root()
    try:
        return _run(args, root)
    except (DesignConfigError, checks.DesignCheckError, DesignError, RestError) as exc:
        print(f"design: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
