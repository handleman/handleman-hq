# 058 Domain Model — Plan

## Approach

1. Inventory the concepts from the code and docs: contract, specs/tasks, run
   statuses, evidence, guards, drivers, acceptance, design, models, ops.
2. Write the glossary first (language), then the model (structure) so each term
   has one home; put implementation mapping only in the model.
3. Record the four hard decisions as ADRs with the alternatives that were
   actually rejected.
4. Link from the README, AGENTS and the app glossary; correct the app's
   `pilot`/`run` overload.
5. Validate: `make test`, `make factory-audit`, and a link/terminology pass.

## Why not one big document

A glossary stays usable only if it is pure language; mixing invariants and file
paths makes it a spec. The model carries structure and mapping. ADRs carry the
"why". Three artifacts, three jobs.

## Verification

- `make test` (docs changes must not disturb code).
- `make factory-audit` (hygiene, no secrets/large blobs).
- Manual: every term in the glossary appears or is implied by the model; every
  invariant has a code/doc owner; links resolve.
