# Target-owned drivers, with a packaged fallback

The four target-specific phases (e2e, acceptance, smoke, db) are commands the
target declares in `swarm.yaml`, run with a JSON parameter object and required
to print one JSON result; an absent driver runs the packaged implementation, and
the source is recorded per phase. We rejected hardcoding the app's paths in the
core (the factory must work for any repo) and rejected in-process plugins (a
target may be another language). The cost is a small protocol and a rule: a
successful driver that prints no JSON is invalid, because silence is not
evidence.

**Considered:** hardcoded commands (rejected: target coupling), Python entry
points (rejected: language lock-in), free-form scripts (rejected: no result
contract).
