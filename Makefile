# handleman-hq — the factory's own entry points.
# The target repo keeps its own Makefile; `hq` runs against the directory it is
# invoked in (SWARM_TARGET), so nothing here is app-specific.

PY ?= python
ARGS ?= ""
CASE ?= ""

test: ## Core + driver unit tests (driver tests skip without an app tree)
	$(PY) -m pytest tests/ -q

test-core: ## Core tests only (no app/driver tree required)
	$(PY) -m pytest tests/ -q -m "not driver"

swarm-health: ## App tests + the e2e suite; non-zero when the stand is broken
	$(PY) -m swarm.drivers.health

swarm-accept: ## Spec acceptance pass (ARGS="--no-queue --selftest")
	$(PY) -m swarm.drivers.acceptance $(ARGS)

provider-audit: ## Key-free reachability probe for every provider in the registry
	$(PY) -m swarm.provider_audit $(ARGS)

factory-audit: ## Block a push that would publish caches, secrets or large blobs
	$(PY) -m swarm.factory_audit

swarm-preflight: ## Validate models/keys/venvs/gates before a run
	$(PY) -m swarm.preflight

swarm-replay: ## Outcome replay suite (models required; compares to replay_baseline.json)
	$(PY) -m swarm.drivers.bench.replay $(ARGS)

swarm-replay-off: ## Same suite with every 021 knob at its 020 value (A/B side)
	$(PY) -m swarm.drivers.bench.replay --off

swarm-bench: ## Bench cases: make swarm-bench ARGS=--list
	$(PY) -m swarm.drivers.bench $(ARGS)

swarm-bench-live: ## Live replay of one case in a throwaway worktree: make swarm-bench-live CASE=<id>
	@test -n "$(CASE)" || { echo "CASE=<corpus id> is required (see: make swarm-bench ARGS=--list)"; exit 2; }
	$(PY) -m swarm.drivers.bench --live $(CASE)

swarm-report: ## Ledger dashboard
	$(PY) -m swarm.report $(ARGS)

swarm-record: ## Record a manually completed task: make swarm-record SPEC=<dir> TASK=<T3>
	@test -n "$(SPEC)" -a -n "$(TASK)" || { echo "SPEC=<spec dir> TASK=<T3> are required"; exit 2; }
	$(PY) -m swarm.record $(SPEC) $(TASK)

up: ## Start the queue and attach the dashboard
	./up.sh

stop: ## Stop the running queue
	./stop.sh

dash: ## Dashboard for the current run
	./dash.sh
