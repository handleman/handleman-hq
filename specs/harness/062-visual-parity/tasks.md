# 062 Visual Parity Gate — Tasks

- [x] T1 (AC-1): Add `evaluate_visual` (region crop, mask, 0.90 default) and
  unit tests for pass/fail/crop/mask/missing baseline.
- [x] T2 (AC-2): Add the strict coverage rule (a design table with no `[[visual]]`
  is a config error) and its test.
- [x] T3 (AC-3): Wire the checker into the acceptance report (issues, `.md`,
  verdict, fix queue) and add an acceptance test that a low-similarity region
  fails the spec.
- [ ] T4 (AC-4): Add the first 041/042 mobile visual regions and pass them
  against the Figma reference at >=90%.
- [ ] T5 (AC-5): Docs, factory suite/ruff/audit, release 0.8.0, app pin, and the
  strict 041/042 acceptance; prove the gate fails on the unstyled builder.
