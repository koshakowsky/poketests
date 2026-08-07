# E2E · Analytics page

Route `/analytics`. Grouping buttons (Type/Color/Generation/Habitat/Shape/
Growth rate) → an ag-grid table → three recharts: **Average Total Stats**
(bar), **By type** (pie), **Pokemons by generation** (bar).

> **🔒 Premium.** This page requires an authenticated **premium** session (a
> fixture signs in a premium user — see [00-overview.md](00-overview.md)).
> The anonymous-redirect and free-tier upgrade-wall behaviors are covered in
> [06-auth.md](06-auth.md) (E2E-AUTH-03) and [07-checkout.md](07-checkout.md)
> (E2E-PAY-01); the cases below assume access is already granted.

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
