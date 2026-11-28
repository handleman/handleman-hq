# 062 Visual Parity Gate — Spec

Status: approved (2026-11-28); the 042 upload exposed the gap.

## What / Why

The 041 design checks compare CSS tokens and region rectangles; they do not
compare the rendered surface. The 042 upload passed every gate and the
interaction e2e while the no-route builder's **Build route** CTA was unstyled
plain text: the markup existed, the CSS did not. Tokens and rects cannot see
that.

This spec adds a deterministic **visual similarity** check to the acceptance
pass. A design spec declares one or more `[[visual]]` regions with a Figma
reference render; the checker crops the actual desktop/mobile screenshot and the
reference to the same region, computes the pixel similarity, and fails the spec
below a configurable minimum (default **90%**). The map and browser chrome are
excluded by region/mask, so live tiles cannot make a correct surface fail. A
design spec in `--strict` must declare at least one visual region.

## Design

`design.toml` gains:

```toml
[[visual]]
frame = "mobile"                 # the acceptance view name
baseline = "designs/<key>/6-53.png"
x = 0
y = 484
w = 390
h = 180
min_similarity = 0.90            # default 0.90
ac = "AC-2"
mask = [{ x = 0, y = 0, w = 0, h = 0 }]   # optional, ignored pixels
```

The deterministic pixel check is the gate. The existing **advisory vision
pass** stays as a second reader: it should use a strong vision model
(`SWARM_ACCEPT_MODEL`, recommended `opencode-go/gemini-4-argon`, fallback
`claude-haiku-5-5`) to name what is missing (an unstyled CTA, a removed toggle)
in the report. A grounded vision finding is recorded and can queue a fix task,
but it never replaces the measured 90% score; a VLM cannot be the only oracle
for geometry.

- The baseline is the Figma reference render from the design cache (gitignored;
  `hq design sync` is the prerequisite, as for every design check).
- The actual image is the existing acceptance screenshot for that view
  (`browser["shots"][frame]`); no new browser collector is needed.
- Both images are normalised to the actual screenshot size, cropped to the
  region, and compared with the same per-pixel threshold as the existing
  screenshot check (`max(channel) > 12`). Similarity = `1 - changed/total`.
- Region coordinates are in the actual viewport; the acceptance views are
  desktop 1280×800 and mobile 390×844. A full-frame entry may set all four
  coordinates to 0, but a design surface normally excludes the map.
- `design_visual` issues carry the similarity and the threshold, e.g.
  `similarity 87.3% < 90.0% (mobile sheet)`, and make the report FAIL.
- In `--strict`, a `design.toml` with a `[[figma]]`/`[[region]]` table and no
  `[[visual]]` entry is a config error: a design spec cannot claim parity
  without a visual check.

## Scope

- `src/swarm/design/checks.py`: `evaluate_visual(table, shots, root)`.
- `src/swarm/drivers/acceptance.py`: run it on every design spec, append the
  issues to `design_issues`, and enforce the strict requirement.
- Tests: crop/region/mask/threshold, a low-similarity failure, a missing
  baseline, and the strict requirement.
- Docs: design/acceptance/run-guards.
- The app's 041/042 `design.toml` add the first regions (product 043 T6).

## Non-goals

- Pixel-diffing live map tiles, browser chrome or fonts/AA.
- Replacing the token/region checks; they stay the cheap first line.
- A vision model deciding green; the vision pass stays advisory.
- A new screenshot collector in the target.

## Acceptance Criteria

- [ ] AC-1: **Similarity.** `evaluate_visual` fails a region below
  `min_similarity` (default 0.90) with the measured similarity, and passes at or
  above it; it handles region crops and masks deterministically.
- [ ] AC-2: **Strict coverage.** `--strict` reports a design spec with no
  `[[visual]]` entry as a config error; a spec with one runs the check.
- [ ] AC-3: **Acceptance integration.** A low-similarity region makes the spec
  FAIL and appears in `acceptance.md`; a missing baseline is a config/failure,
  not a skip; `run.json`/the report carries the similarity.
- [ ] AC-4: **First regions.** 041 and 042 declare at least one mobile visual
  region (the sheet chrome; the builder header/summary for 042) and pass at
  >=90% against the Figma reference.
- [ ] AC-5: **Verification.** Unit tests, the factory suite, ruff and
  `factory-audit` are green; release 0.8.0; docs updated.

## Verification

`pytest tests/test_design.py tests/test_acceptance.py`, the factory suite, ruff
and `factory-audit`; `make swarm-accept --strict` on 041/042 with the design
cache synced; a deliberately unstyled builder must fail the visual region.
