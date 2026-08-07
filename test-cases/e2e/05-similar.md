# E2E · Similar page

Route `/similar`. Autocomplete → pick a pokemon → a **target card** (official
sprite, base stats, meta) + a **Similar Pokemon** ag-grid (match %) + a radar
("X vs Top-3 similar"). Shows `⏳ Loading...` while fetching.

> **🔒 Premium.** Requires an authenticated **premium** session (fixture —
> see [00-overview.md](00-overview.md)); anonymous/free access behavior lives in
> [06-auth.md](06-auth.md) / [07-checkout.md](07-checkout.md).

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-SIM-01 | Pick a target → card + table + radar | P0 | journey *(matrix)* |
| E2E-SIM-02 | Similar list ordered by match % | P2 | journey |
| E2E-SIM-03 | Target card shows meta | P2 | render |

---

### E2E-SIM-01 — Pick a target → card + table + radar · P0 · journey *(matrix)*
**Steps:** open `/similar`; type `bulbasaur`; click the `#1 bulbasaur`
suggestion; wait for results (the `⏳ Loading...` indicator resolves).
**Expected:**
- a target card shows `#001`, `bulbasaur`, its type badges and six stat bars;
- a `Similar Pokemon (N)` heading and an ag-grid with ≥1 `.ag-row`, each row
  showing a `Match` percentage;
- the radar card `bulbasaur vs Top-3 similar` renders a `svg.recharts-surface`.
*testid:* `similar-search`, `target-card`, `similar-grid`, `similar-radar`.

### E2E-SIM-02 — Similar list ordered by match % · P2 · journey
**Steps:** pick bulbasaur (as above); read the `Match` column top-to-bottom.
**Expected:** percentages are non-increasing (highest match first); the top
entry is a close relative (e.g. ivysaur). Ordering correctness is API-tested;
here we confirm the UI presents it in order.

### E2E-SIM-03 — Target card shows meta · P2 · render
**Steps:** pick bulbasaur.
**Expected:** the target card's meta row shows height (`…m`), weight (`…kg`),
habitat, generation (`Gen 1`) and capture rate — the detail fields the
`GET /api/pokemon/{id}` response carries.
