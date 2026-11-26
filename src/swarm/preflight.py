"""Preflight before the first LLM call (012 T12).

Checks that the configured roles can actually run: env model ids, provider
keys, Ollama reachability + pulled image, cloud model availability, the two
venvs, and the gate binaries. Never prints secret values.

Run standalone: `make swarm-preflight` (or `python -m swarm.preflight`).
Set `SWARM_SKIP_PREFLIGHT=1` to bypass inside a pilot.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from swarm.paths import REPO_ROOT

# Preflight is the one command an operator runs *before* anything else, so it
# must see the same `.env` the run will (026 T8 made the model list read from
# `os.environ` directly; without this the roles printed `<missing>`).
try:
    from dotenv import load_dotenv

    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:  # python-dotenv is optional for the unit tests
    pass

# Roles that the crew actually instantiates (zen fallback is Phase 1 / T13).
# 047: the role list lives in swarm.model_config (the one table).
from swarm.model_config import FALLBACK_VARS, OPTIONAL_ROLE_VARS, ROLE_VARS

GATE_BINARIES = ("pytest", "ruff", "mypy")


def _gate_binaries(env: dict[str, str]) -> tuple[str, ...]:
    """First executable of each `SWARM_GATE_COMMANDS` entry (or Python defaults)."""
    raw = env.get("SWARM_GATE_COMMANDS", "").strip()
    if not raw:
        return GATE_BINARIES
    binaries: list[str] = []
    for command in re.split(r"[;\n]", raw):
        try:
            argv = shlex.split(command)
        except ValueError:
            continue
        if argv:
            binaries.append(argv[0])
    return tuple(dict.fromkeys(binaries)) or GATE_BINARIES
OPTIONAL_BINARIES = ("npm",)  # frontend gate only when vitest is installed

DEFAULT_OLLAMA = "http://localhost:11434"
DEFAULT_ZEN = "https://opencode.ai/zen/v1"
DEFAULT_GO = "https://opencode.ai/inference/go/openai/v1"
USER_AGENT = "comfort-walking-router/0.1 (swarm-preflight)"
OPENROUTER_MODELS = "https://openrouter.ai/api/v1/models"


@dataclass(frozen=True)
class Problem:
    check: str
    detail: str

    def __str__(self) -> str:
        return f"{self.check}: {self.detail}"


def provider(model: str) -> str:
    """047: one router from swarm.model_config."""
    from swarm.model_config import provider as _provider

    return _provider(model)


def model_id(model: str) -> str:
    for prefix in ("ollama/", "zen/", "opencode-go/", "openrouter/"):
        if model.startswith(prefix):
            return model.removeprefix(prefix)
    return model


def is_free_model(model: str) -> bool:
    """047: delegate to the one predicate in swarm.model_config."""
    from swarm.model_config import is_free

    return is_free(model)


def _get_json(url: str, *, headers: dict[str, str] | None = None, timeout: float = 8.0) -> Any:
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json", **(headers or {})}
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _http_status(url: str, *, timeout: float = 6.0) -> tuple[int | None, str]:
    """(status, error) for a key-free reachability probe (055 AC-4)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200)), ""
    except urllib.error.HTTPError as e:
        return int(e.code), ""
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return None, str(e)


def probe_provider(
    name: str,
    env: dict[str, str] | None = None,
    *,
    status: Callable[[str], tuple[int | None, str]] = _http_status,
) -> tuple[str, str]:
    """Classify a provider without a key: reachable/auth-required/wrong-base/unreachable/incident."""
    from swarm import providers as _providers

    url = _providers.probe_url(name, env)
    if not url:
        return "none", "no probe URL"
    code, error = status(url)
    if code is None:
        return "unreachable", error or "no response"
    if 200 <= code < 300:
        return "reachable", url
    if code in (401, 403):
        return "auth-required", url
    if 300 <= code < 400:
        return "wrong-base", f"{code} redirect from {url}"
    if code == 404:
        return "wrong-base", f"404 at {url}"
    if code >= 500:
        return "incident", f"{code} at {url}"
    return "error", f"{code} at {url}"


def _ping_model_ids(env: dict[str, str], fetch: Callable[..., Any]) -> dict[str, set[str]]:
    """Available model ids per cloud provider (one request each)."""
    avail: dict[str, set[str]] = {}
    if any(provider(env.get(v, "")) == "openrouter" for v in ROLE_VARS):
        try:
            data = fetch(OPENROUTER_MODELS)
        except Exception as e:
            raise RuntimeError(f"openrouter model list: {e}") from e
        avail["openrouter"] = {m["id"] for m in data.get("data", [])}
    if any(provider(env.get(v, "")) == "zen" for v in ROLE_VARS + OPTIONAL_ROLE_VARS):
        base = env.get("SWARM_ZEN_BASE_URL", DEFAULT_ZEN).rstrip("/")
        try:
            data = fetch(
                f"{base}/models",
                headers={"Authorization": f"Bearer {env.get('OPENCODE_API_KEY', '')}"},
            )
        except Exception as e:
            raise RuntimeError(f"zen model list: {e}") from e
        avail["zen"] = {m["id"] for m in data.get("data", [])}
    if any(
        provider(env.get(v, "")) == "opencode-go" for v in ROLE_VARS + OPTIONAL_ROLE_VARS
    ):
        # The Go catalogue is where the role ids live; a typo here would only
        # surface after the first task, so check it before the first call.
        base = env.get("SWARM_GO_BASE_URL", DEFAULT_GO).rstrip("/")
        key = env.get("OPENCODE_GO_API_KEY") or env.get("OPENCODE_API_KEY", "")
        try:
            data = fetch(
                f"{base}/models",
                headers={"Authorization": f"Bearer {key}", "User-Agent": USER_AGENT},
            )
        except Exception as e:
            raise RuntimeError(f"opencode-go model list: {e}") from e
        avail["opencode-go"] = {m["id"] for m in data.get("data", [])}
    return avail


def _available_ollama(base: str, fetch: Callable[..., Any]) -> set[str]:
    data = fetch(f"{base.rstrip('/')}/api/tags")
    names: set[str] = set()
    for m in data.get("models", []):
        name = m.get("name") or m.get("model") or ""
        if name:
            names.add(name.removesuffix(":latest"))
    return names


def _run(cmd: list[str], timeout: int) -> bool:
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout, check=False
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def self_heal(
    env: dict[str, str] | None = None,
    *,
    log: Callable[[str], None] = print,
) -> list[str]:
    """Best-effort environment repair before checks (015 AC-10).

    Only missing local artefacts are rebuilt; auth/base-URL failures stay
    terminal because nothing local can fix them.
    """
    env = dict(os.environ if env is None else env)
    if env.get("SWARM_SELF_HEAL", "1") != "1":
        return []
    actions: list[str] = []
    root = REPO_ROOT
    needs_venv = not (root / ".venv" / "bin" / "python").exists()
    if needs_venv and _run(["make", "dev-setup-python"], timeout=900):
        actions.append("bootstrapped .venv")
    needs_frontend = (root / "frontend" / "package.json").is_file() and not (
        root / "frontend" / "node_modules"
    ).is_dir()
    if needs_frontend and _run(["npm", "--prefix", "frontend", "ci"], timeout=900):
        actions.append("installed frontend deps")
    else:
        # A task added a devDependency (e.g. vitest in 007-T1) but the coder cannot
        # run `npm install`; install it here so the gate sees the dependency.
        deps_missing = (root / "frontend" / "node_modules").is_dir() and not _run(
            ["npm", "--prefix", "frontend", "ls", "--depth=0"], timeout=120
        )
        if deps_missing and _run(["npm", "--prefix", "frontend", "install"], timeout=900):
            actions.append("installed newly added frontend deps")
    modelfiles = {
        "swarm-qa": root / "swarm" / "ollama" / "Modelfile.qa",
        "swarm-coder": root / "swarm" / "ollama" / "Modelfile",
    }
    for var in ROLE_VARS:
        model = env.get(var, "").strip()
        if provider(model) != "ollama":
            continue
        name = model_id(model).removesuffix(":latest")
        modelfile = modelfiles.get(name)
        if modelfile is None or not modelfile.is_file():
            continue
        if _run(["ollama", "show", name], timeout=30):
            continue
        if _run(["ollama", "create", name, "-f", str(modelfile)], timeout=600):
            actions.append(f"built ollama image {name}")
    for action in actions:
        log(f"self-heal: {action}")
    return actions


ROLE_FACTORIES: tuple[tuple[str, str], ...] = (
    # The same flags the crews use: the planner may be paid (build_plan_crew
    # passes allow_paid=True), the reviewer/senior/verifier follow
    # SWARM_ALLOW_PAID through `_paid_ok(None)`.
    ("planner", "planner"),
    ("coder", "coder"),
    ("reviewer", "reviewer"),
    ("senior", "senior"),
    ("verifier", "verifier"),
)


def factories() -> dict[str, Callable[[], Any]]:
    """Role → factory used by the crews, built with the crews' own flags."""
    from swarm import llms

    return {
        "planner": lambda: llms.planner_llm(allow_paid=True),
        "coder": llms.coder_llm,
        "reviewer": llms.reviewer_llm,
        "senior": llms.senior_llm,
        "verifier": llms.verifier_llm,
    }


def factory_problems() -> list[Problem]:
    """Build every role factory exactly as the run will (026 AC-9).

    A paid planner with `allow_paid=False` used to end as a 2-second
    `crew_error` with no message: the factory raised inside the crew, not in
    preflight, because preflight built a different factory with different flags.
    """
    problems: list[Problem] = []
    for name, factory in factories().items():
        try:
            factory()
        except Exception as e:  # noqa: BLE001 - report every broken factory
            problems.append(
                Problem(f"factory {name}", f"{type(e).__name__}: {e}"[:400])
            )
    return problems


def probe_roles(
    *,
    offline: bool = False,
    roles: dict[str, Callable[[], Any]] | None = None,
    call: Callable[[Any], Any] | None = None,
) -> list[Problem]:
    """One 1-token call per configured role (026 AC-5).

    A free-tier wall must fail before the first task, not after 20 minutes of
    retries. `--offline` skips it; the in-run preflight opts in with
    `SWARM_PREFLIGHT_PROBE=1` because five tiny calls are not free.
    """
    if offline:
        return []
    problems: list[Problem] = []
    invoke = call or (lambda llm: llm.call(
        [{"role": "user", "content": "Reply with the single word: ok"}]
    ))
    for name, factory in (roles or factories()).items():
        try:
            invoke(factory())
        except Exception as e:  # noqa: BLE001 - a walled role is a preflight problem
            problems.append(
                Problem(f"probe {name}", f"{type(e).__name__}: {e}"[:400])
            )
    return problems


def unmerged_paths(repo_root: Path | None = None) -> list[str]:
    """Paths with unresolved index stages (mid-merge, rebase, or stash pop)."""
    try:
        p = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=repo_root or REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return sorted({line.strip() for line in p.stdout.splitlines() if line.strip()})


def check(
    env: dict[str, str] | None = None,
    *,
    fetch: Callable[..., Any] = _get_json,
    which: Callable[[str], str | None] = shutil.which,
    offline: bool = False,
    probe_factories: bool = False,
    probe: bool = False,
    status: Callable[[str], tuple[int | None, str]] = _http_status,
) -> list[Problem]:
    """Return every blocking problem; empty list means safe to start.

    `probe_factories` builds the real role factories (process env, same flags as
    the crews). It is opt-in so a unit test with a synthetic env never depends
    on the machine's keys.
    """
    env = dict(os.environ if env is None else env)
    self_heal(env)
    problems: list[Problem] = []
    allow_paid = env.get("SWARM_ALLOW_PAID", "0") == "1"
    if probe_factories:
        problems.extend(factory_problems())

    # 0. A conflicted worktree poisons every gate and can be committed by the
    #    next green run; stop before the first paid call.
    conflicts = unmerged_paths()
    if conflicts:
        problems.append(
            Problem(
                "worktree",
                "unmerged paths — resolve them or `git merge --abort` before a run: "
                + ", ".join(conflicts[:6]),
            )
        )

    # 1. Model ids present, free-guard, provider key present.
    for var in ROLE_VARS + OPTIONAL_ROLE_VARS:
        model = env.get(var, "").strip()
        if not model:
            if var in OPTIONAL_ROLE_VARS:
                continue  # documented default (verifier → senior model)
            problems.append(Problem(var, "not set (copy .env.example → .env and fill it in)"))
            continue
        if model != env.get(var, ""):
            problems.append(Problem(var, "leading/trailing whitespace in model id"))
        prov = provider(model)
        if not is_free_model(model) and not allow_paid:
            problems.append(
                Problem(var, f"paid model {model} (needs SWARM_ALLOW_PAID=1 + allow_paid)")
            )
        if prov == "openrouter" and not env.get("OPENROUTER_API_KEY"):
            problems.append(Problem(var, "uses OpenRouter but OPENROUTER_API_KEY is empty"))
        if prov == "zen" and not env.get("OPENCODE_API_KEY"):
            problems.append(Problem(var, "uses Zen but OPENCODE_API_KEY is empty"))
        if prov == "opencode-go" and not (
            env.get("OPENCODE_GO_API_KEY") or env.get("OPENCODE_API_KEY")
        ):
            problems.append(
                Problem(var, "uses OpenCode Go but OPENCODE_GO_API_KEY is empty")
            )

    # 1c. Provider registry (055 T3): the id must name a known prefix and carry
    # the credential that prefix needs; subscriptions point at the proxy route.
    from swarm import providers as _providers

    for var in ROLE_VARS + OPTIONAL_ROLE_VARS:
        model = env.get(var, "").strip()
        if not model:
            continue
        resolved = _providers.resolve(model)
        if resolved is None:
            if os.getenv("SWARM_STRICT_PREFIXES", "1") != "0":
                problems.append(
                    Problem(
                        var,
                        f"{model} has no known provider prefix — use one of "
                        + ", ".join(_providers.known_prefixes())
                        + " (docs/providers.md)",
                    )
                )
            continue
        if resolved.kind == "subscription":
            problems.append(
                Problem(
                    var,
                    f"{resolved.name} is a subscription model: sign in through a local "
                    "LiteLLM proxy (docs/providers.md#subscriptions)",
                )
            )
            continue
        if resolved.kind in {"native", "gateway", "openai_compatible"} and not (
            _providers.has_key(resolved.name, env)
        ):
            hint = resolved.keys[0] if resolved.keys else "a credential"
            problems.append(
                Problem(var, f"set {hint} for {resolved.name} (docs/providers.md#{resolved.name})")
            )
        if resolved.base_env:
            base = str(env.get(resolved.base_env, "")).strip()
            if base and not base.startswith(("http://", "https://")):
                problems.append(Problem(var, f"{resolved.base_env} must be an http(s) URL"))

    # 1b. Fallback ids are real model ids too (047 AC-6). The 2026-11-22 bug was
    # a Go id sitting in SWARM_LOCAL_FALLBACK_MODEL as if it were OpenRouter:
    # nothing validated it until the first call after a quota wall.
    for var in FALLBACK_VARS:
        model = env.get(var, "").strip()
        if not model:
            continue
        prov = provider(model)
        if not is_free_model(model) and not allow_paid:
            problems.append(
                Problem(var, f"paid fallback {model} (needs SWARM_ALLOW_PAID=1 + allow_paid)")
            )
        if prov == "openrouter" and not env.get("OPENROUTER_API_KEY"):
            problems.append(
                Problem(var, "fallback uses OpenRouter but OPENROUTER_API_KEY is empty")
            )
        if prov == "zen" and not env.get("OPENCODE_API_KEY"):
            problems.append(Problem(var, "fallback uses Zen but OPENCODE_API_KEY is empty"))
        if prov == "opencode-go" and not (
            env.get("OPENCODE_GO_API_KEY") or env.get("OPENCODE_API_KEY")
        ):
            problems.append(
                Problem(var, "fallback uses OpenCode Go but OPENCODE_GO_API_KEY is empty")
            )

    # 2. Local/cloud model availability.
    if not offline:
        ollama_roles = [
            env.get(v, "").strip()
            for v in ROLE_VARS + OPTIONAL_ROLE_VARS + FALLBACK_VARS
            if provider(env.get(v, "")) == "ollama"
        ]
        if ollama_roles:
            base = env.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA)
            try:
                have = _available_ollama(base, fetch)
            except Exception as e:  # noqa: BLE001 - report reachability, don't crash
                problems.append(Problem("ollama", f"not reachable at {base}: {e}"))
            else:
                for model in ollama_roles:
                    want = model_id(model).removesuffix(":latest")
                    if want not in have:
                        problems.append(
                            Problem("ollama", f"{model} is not pulled (have: {sorted(have)})")
                        )
        try:
            avail = _ping_model_ids(env, fetch)
        except Exception as e:  # noqa: BLE001
            problems.append(Problem("cloud", f"model list request failed: {e}"))
        else:
            for var in ROLE_VARS + OPTIONAL_ROLE_VARS + FALLBACK_VARS:
                model = env.get(var, "").strip()
                prov = provider(model) if model else ""
                if prov in avail and model_id(model) not in avail[prov]:
                    problems.append(
                        Problem(var, f"{model_id(model)} is not offered by {prov} right now")
                    )

    # 3. The target venv + gate binaries (same PATH the Guarded Shell uses).
    #    The harness runs on this interpreter, so only the app venv must exist;
    #    a vendored checkout's `swarm/.venv` is added to PATH when present.
    import sys as _sys

    from swarm import contract as _contract

    app_venv = _contract.current(REPO_ROOT).python_venv
    app_python = REPO_ROOT / app_venv / "bin" / "python"
    if not app_python.exists():
        problems.append(
            Problem("app venv", f"missing {app_python} (run `make dev-setup`)")
        )
    bins = [REPO_ROOT / app_venv / "bin", Path(_sys.executable).parent]
    path_env = os.pathsep.join([str(b) for b in bins if b.exists()] + [env.get("PATH", "")])
    for binary in _gate_binaries(env):
        if not which(binary, path=path_env):
            problems.append(Problem("gates", f"`{binary}` not found in the project venvs"))

    # 4b. Key-free reachability probe (055 AC-4): before a paid run, prove the
    # provider is reachable and the base URL is right — no registration needed.
    if probe:
        from swarm import providers as _providers

        used = {
            p.name
            for p in (
                _providers.resolve(env.get(v, "").strip())
                for v in ROLE_VARS + OPTIONAL_ROLE_VARS
            )
            if p is not None
        }
        for name in sorted(used):
            verdict, detail = probe_provider(name, env, status=status)
            keyed = _providers.has_key(name, env)
            if verdict in {"unreachable", "wrong-base", "incident", "error"}:
                problems.append(Problem(f"{name} probe", f"{verdict}: {detail}"))
            elif verdict == "auth-required" and keyed:
                problems.append(
                    Problem(f"{name} probe", "the configured key was rejected (401/403)")
                )
            # no key + 401/403 = reachable and auth is expected: not a problem.

    # 4. Browser e2e: a task whose brief names an e2e spec needs a runnable
    #    suite (026 AC-8). Cheap: file existence, no browser launch.
    if (REPO_ROOT / "frontend" / "e2e").is_dir():
        from swarm.drivers import e2e as e2e_suite

        for problem in e2e_suite.available(REPO_ROOT):
            problems.append(Problem("e2e", problem))
    return problems


def spec_kind_notes(repo_root: Path | None = None) -> list[str]:
    """Informational drift between the spec folders/`kind` files and HARNESS_SPECS (034)."""
    from swarm.flow import HARNESS_SPECS
    from swarm.spec_loader import iter_spec_dirs, spec_kind

    root = Path(repo_root or REPO_ROOT)
    notes: list[str] = []
    for path in iter_spec_dirs(root):
        if not (path / "tasks.md").is_file():
            continue
        kind = spec_kind(root, path.name)
        if kind == "harness" and path.name not in HARNESS_SPECS:
            notes.append(
                f"{path.name} is harness but not in HARNESS_SPECS "
                "(the queue still skips it by kind)"
            )
        if path.name in HARNESS_SPECS and kind != "harness":
            notes.append(
                f"{path.name} is in HARNESS_SPECS but does not resolve to a harness spec"
            )
    return notes


def frontend_lock_problem(repo_root: Path | None = None) -> list[Problem]:
    """The JS lockfile must be in sync with its package.json (041 deploy).

    `npm ci` in a deploy build is strict: a stale lock (deps added without
    regenerating it) fails the build. Catch it here with `npm ci --dry-run` so a
    green run can never ship a lock that won't build. The directory is declared
    by the target's `swarm.yaml` (`lock_dir`); no declaration, no check.
    """
    from swarm import contract as _contract

    root = Path(repo_root or REPO_ROOT)
    lock_dir = _contract.current().lock_dir
    if not lock_dir:
        return []
    frontend = root / lock_dir
    if not (frontend / "package.json").is_file():
        return []
    try:
        p = subprocess.run(
            ["npm", "ci", "--dry-run"],
            cwd=frontend,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []  # npm missing here; not a preflight problem
    if p.returncode == 0:
        return []
    missing = [
        line.strip()
        for line in (p.stdout + p.stderr).splitlines()
        if "from lock file" in line
    ]
    return [
        Problem(
            "js lock",
            "package-lock.json is out of sync with package.json (npm ci would fail). "
            "Run `make npm-lock-check` / `npm install` in the lock directory. "
            + "; ".join(missing[:3]),
        )
    ]


def price_warnings(env: dict[str, str] | None = None) -> list[str]:
    """Paid role models with no price row (055 AC-6): cost is None, cap inert."""
    from swarm.usage import _rate

    source = os.environ if env is None else env
    out: list[str] = []
    for var in ROLE_VARS + OPTIONAL_ROLE_VARS:
        model = str(source.get(var, "")).strip()
        if not model or is_free_model(model):
            continue
        if _rate(model) is None:
            out.append(
                f"{var} {model} has no price row — cost is None and "
                "SWARM_MAX_COST_PER_TASK cannot fire (add it to usage.py)"
            )
    return out


def database_note() -> str:
    """One informational line about the local Postgres (never a failure).

    005's saved-routes tests and the `preferences` e2e specs skip without a
    database; a preflight that says "down" saves the "why did these skip?"
    question. `make swarm-db-up` starts it.
    """
    import subprocess

    script = REPO_ROOT / "swarm" / "db.sh"
    if not script.is_file():
        return "database: no swarm/db.sh"
    try:
        out = subprocess.run(
            [str(script), "status"], capture_output=True, text=True, timeout=30, check=False
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"database: unknown ({exc})"
    return f"database: {out or 'unknown'}"


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Validate swarm model/venv configuration.")
    ap.add_argument("--offline", action="store_true", help="skip provider model-list requests")
    ap.add_argument(
        "--probe",
        action="store_true",
        default=os.getenv("SWARM_PREFLIGHT_PROBE", "0") == "1",
        help="key-free reachability probe per used provider (no registration needed)",
    )
    args = ap.parse_args()

    for var in ROLE_VARS + OPTIONAL_ROLE_VARS:
        model = os.getenv(var, "")
        shown = model or ("<senior model>" if var in OPTIONAL_ROLE_VARS else "<missing>")
        print(f"{var:<24} {shown:<58} {provider(model) if model else '-'}")

    # Reuse the crews' factories so a broken factory (not just a broken id) is
    # caught, with the same allow_paid/fallback flags the run uses.
    problems = list(factory_problems())

    # One 1-token call per role: a wall fails here, not after the first task.
    if not args.offline:
        print(database_note())
    for note in spec_kind_notes():
        print(f"spec-kind: {note}")
    problems += probe_roles(offline=args.offline)
    problems += check(offline=args.offline, probe=args.probe)
    problems += frontend_lock_problem()
    for warning in price_warnings():
        print(f"price: {warning}")
    for p in problems:
        print(f"FAIL {p}")
    if problems:
        print(f"\n{len(problems)} preflight problem(s) — fix before running the pilot.")
        return 1
    print("\npreflight OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())