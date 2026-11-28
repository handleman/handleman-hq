# 062 Visual Parity Gate — Plan

1. Add `evaluate_visual(table, shots, root)` to `swarm/design/checks.py`:
   - resolve the actual screenshot from `shots[frame]` and the baseline from
     `root/baseline`;
   - normalise both to the actual size, crop to `(x,y,w,h)`, mask the optional
     rects, and compute `similarity = 1 - changed/total` with the existing
     `max(channel) > 12` pixel rule;
   - emit `design_visual` issues with the measured similarity and threshold;
   - default `min_similarity` to 0.90.
2. In `drivers/acceptance.py`, after the existing design evaluation, call
   `evaluate_visual(table, browser.get("shots") or {}, root=root)` and append
   the issues to `report.design_issues` (so the report, verdict and fix queue
   agree). In `--strict`, add a config error for a design table with no
   `[[visual]]` entry.
3. Unit tests in `tests/test_design.py`: exact pass, a 5% block failing at
   0.90, a region crop ignoring differences outside it, a mask ignoring a
   known-different area, a missing baseline, and the strict requirement in
   `tests/test_acceptance.py`.
4. Add the first regions to the app's 041/042 `design.toml` (product 043 T6):
   mobile sheet header/summary against `designs/<key>/6-53.png`, excluding the
   map; desktop optional.
5. Docs: `docs/design.md`, `docs/testing.md`, `docs/run-guards.md`; release
   0.8.0, pin the app, and run the strict acceptance on 041/042.
6. Verify the gate can fail: temporarily remove the builder CSS in a scratch
   copy (or assert a synthetic region against the unstyled screenshot) and see
   `design_visual` below 90%. Do not commit the scratch change.

## Risks

- A Figma render includes mocked browser chrome; regions must be cropped below
  it. The first entries target the mobile sheet, which has no chrome.
- Live map tiles differ from the design's static map; a region that includes the
  map is not a valid parity check. The builder/summary region is chrome-only.
- Font rendering/AA differs by platform; the 90% threshold and the 12-level
  pixel tolerance leave room, while a missing pill (a large block of brand
  colour) still fails.
- The design cache is gitignored; a machine without a synced cache fails the
  check rather than silently skipping it (intended for a design spec).
