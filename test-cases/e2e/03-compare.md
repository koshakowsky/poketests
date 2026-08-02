# E2E · Compare page

Route `/compare`. Autocomplete search → add pokemon as **chips** (max 6) → the
`⚡ Compare` button (shown at ≥2) → a stat-comparison ag-grid + a **radar
chart** ("Feature Profiles").

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-CMP-01 | Autocomplete suggests matches | P1 | journey |
| E2E-CMP-02 | Compare two → table + radar render | P0 | journey *(matrix)* |
| E2E-CMP-03 | Compare button hidden below 2 selected | P2 | render |
| E2E-CMP-04 | Remove a chip | P2 | journey |
| E2E-CMP-05 | Cap at 6 selections | P3 | journey |

---

### E2E-CMP-01 — Autocomplete suggests matches · P1 · journey
**Steps:** in the search box (placeholder `Start typing the Pokemon's name...`)
type `bulba`; wait for the dropdown.
**Expected:** a suggestions dropdown appears containing an entry
`#1 bulbasaur` with its type badges. *testid:* `compare-search`,
`compare-suggestion`.

### E2E-CMP-02 — Compare two → table + radar render · P0 · journey *(matrix)*
**Steps:** search `bulbasaur` → click the suggestion (chip added); search
`charmander` → click the suggestion (2nd chip); click `⚡ Compare`; wait for
results (button shows `Comparing...` then results appear).
**Expected:**
- two chips are shown (`bulbasaur`, `charmander`);
- a comparison grid renders with a pinned `Stat` column and one column per
  pokemon (`Bulbasaur`, `Charmander`), rows `HP…TOTAL`;
- the radar card `Feature Profiles` renders a `svg.recharts-surface` with both
  names in its legend.
*testid:* `compare-chip`, `compare-run`, `compare-grid`, `compare-radar`.

### E2E-CMP-03 — Compare button hidden below 2 · P2 · render
**Steps:** add a single pokemon.
**Expected:** with 0 or 1 chips the `⚡ Compare` button is **not** present; it
appears only once a second chip is added.

### E2E-CMP-04 — Remove a chip · P2 · journey
**Steps:** add two pokemon; click the `×` on the first chip.
**Expected:** that chip disappears (one chip remains); any previously shown
comparison result is cleared.

### E2E-CMP-05 — Cap at 6 selections · P3 · journey
**Steps:** add six pokemon; attempt to add a seventh via the search.
**Expected:** the selection stays at six chips — the seventh is not added
(the UI blocks beyond the API's 2..6 rule; the 400 path itself is API-tested).
