# E2E · Select page (search & filter)

Route `/`. Filters (name, type, generation, group, stat sliders) → a total
counter and an ag-grid table → click a row → a detail card with stat bars →
pagination. Search **debounces ~350 ms**; wait on outcomes, not time.

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-SRCH-01 | Default results load | P0 | smoke *(matrix)* |
| E2E-SRCH-02 | Filter by name narrows the grid | P0 | journey *(matrix)* |
| E2E-SRCH-03 | Row click opens the detail card | P0 | journey *(matrix)* |
| E2E-SRCH-04 | Filter by type | P1 | journey |
| E2E-SRCH-05 | Valid-empty: generation with no data | P2 | journey |
| E2E-SRCH-06 | Pagination Next / Prev | P1 | journey |
| E2E-SRCH-07 | Reset filters | P2 | journey |
| E2E-SRCH-08 | API failure shows the error banner | P2 | negative |

---

### E2E-SRCH-01 — Default results load · P0 · smoke *(matrix)*
**Steps:** open `/`; wait for grid rows.
**Expected:** the counter reads **151** next to `Pokemon found`; the grid has
≥1 `.ag-row`; default sort is by Total desc, so the first row is **mewtwo**.
*testid:* `results-total`, `results-grid`, `grid-row`.

### E2E-SRCH-02 — Filter by name narrows the grid · P0 · journey *(matrix)*
**Steps:** type `char` into the Name field (placeholder `Pikachu...`); wait
for the grid to settle (debounce).
**Expected:** the counter drops to **3**; grid rows are exactly charmander,
charmeleon, charizard (names contain `char`). Waiting on the row-count outcome
covers the debounce implicitly — no sleep.

### E2E-SRCH-03 — Row click opens the detail card · P0 · journey *(matrix)*
**Steps:** open `/`; click the row for **bulbasaur** (filter by name first for
determinism).
**Expected:** a detail card appears showing `#001`, name `bulbasaur`,
`Total 318`, its type badges (grass, poison) and six stat bars (HP…Speed).
*testid:* `selected-card`.

### E2E-SRCH-04 — Filter by type · P1 · journey
**Steps:** select `fire` in the Type multi-select; wait for the grid.
**Expected:** counter `> 0`; every visible row's Types cell contains a `fire`
badge; charmander (#4) is present. (Deep type-filter correctness is API-tested;
here we confirm the control drives the grid.)

### E2E-SRCH-05 — Valid-empty: generation with no data · P2 · journey
**Steps:** choose `Generation 2` in the Generation select.
**Expected:** counter reads **0**; the grid shows no data rows (empty state),
no error banner — an empty result is a valid state, not a failure.

### E2E-SRCH-06 — Pagination Next / Prev · P1 · journey
**Steps:** on default results, note the range label `1–50 of 151`; click
`Next ›`; then `‹ Prev`.
**Expected:** after Next the label reads `51–100 of 151` and the grid's first
row changes; after Prev it returns to `1–50 of 151`. On page 1 `‹ Prev` is
disabled; `Next ›` is enabled while more pages remain.

### E2E-SRCH-07 — Reset filters · P2 · journey
**Steps:** apply a name filter (counter < 151); click `Reset filters`.
**Expected:** the Name field clears and the counter returns to **151**.

### E2E-SRCH-08 — API failure shows the error banner · P2 · negative
**Steps:** intercept `**/api/pokemon/**` and force a 500 (Playwright route
mocking); open `/`.
**Expected:** the error banner `Failed to load Pokemon. Is the API running?`
is visible; the app does not crash (header/nav still rendered). Verifies the
UI's error path — unreachable through the real green stack, so it is driven by
request interception.
