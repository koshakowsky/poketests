# E2E · Analytics page

Route `/analytics`. Grouping buttons (Type/Color/Generation/Habitat/Shape/
Growth rate) → an ag-grid table → three recharts: **Average Total Stats**
(bar), **By type** (pie), **Pokemons by generation** (bar).

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-ANL-01 | Page loads: table + three charts | P0 | smoke/render *(matrix)* |
| E2E-ANL-02 | Switching group updates the table | P1 | journey |
| E2E-ANL-03 | Chart titles present | P2 | render |

---

### E2E-ANL-01 — Page loads: table + three charts · P0 · smoke/render *(matrix)*
**Steps:** open `/analytics`; wait for the grid and charts.
**Expected:** the category grid has ≥1 `.ag-row`; three `svg.recharts-surface`
elements are rendered (one per chart). Charts drawing at all is the core UI
signal here. *testid:* `analytics-grid`, `chart-avg-total`, `chart-by-type`,
`chart-by-generation`.

### E2E-ANL-02 — Switching group updates the table · P1 · journey
**Steps:** with the default `Type` grouping, capture the first `Category` cell;
click the `Color` group button; wait for the grid to refresh.
**Expected:** the `Color` button becomes active and the grid's category values
change (now colors, e.g. `red`/`blue`, not type names). Confirms the control is
wired to the `group_by` query.

### E2E-ANL-03 — Chart titles present · P2 · render
**Steps:** open `/analytics`.
**Expected:** the headings `Average Total Stats`, `By type` and
`Pokemons by generation` are visible above their charts.
