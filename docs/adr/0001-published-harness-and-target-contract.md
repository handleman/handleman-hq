# The harness is a published package; the target declares a contract

The factory is distributed as `handleman-hq` and installed into a target repo;
the target declares its specs dir, scope, gates, drivers and run directory in
one `swarm.yaml`. We rejected vendoring a `swarm/` tree in every target (the
copies drift and every improvement is a multi-repo merge) and rejected a
monorepo (the target must remain a normal app). The cost is an install/upgrade
step and a compatibility surface: unknown contract keys are tolerated, known
ones are typed, and the target pin is explicit.

**Considered:** vendored harness (rejected: drift), monorepo (rejected: coupling),
per-target fork (rejected: no shared fixes).
