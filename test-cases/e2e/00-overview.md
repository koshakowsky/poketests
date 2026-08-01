# E2E (UI) Test Catalog — approach

The top of the pyramid: end-to-end tests that drive the **frontend** in a real
browser and assert what the user sees. Automated later with **Playwright for
Python**; this catalog is the design layer, in the same annotated style as the
API catalog.

## What E2E is for here (and what it is NOT)

E2E is **thin and expensive**, so it verifies the things only a browser can:

- the UI **renders** (grids fill, charts draw, cards appear);
- the UI is **wired** to the API and reflects responses;
- **interactions** work (typing, clicking, routing, pagination);
- it holds up **across browsers**.

E2E does **not** re-test business logic or input combinations — that is fully
covered at the API layer (filters, boundaries, pairwise, error codes). Driving
all filter permutations through the UI would be slow and redundant. Rule: if a
check does not need the browser, it belongs one layer down.

## System under test

The built React SPA served by nginx (same `docker compose` stack). Pages
(from the nav): **Select** `/`, **Analytics** `/analytics`, **Compare**
`/compare`, **Similar** `/similar`. Header shows the logo and a `Gen I` badge.
Data is the hermetic Gen I fixture (151 pokemon) — the same deterministic
anchors as the API catalog (bulbasaur #1, charmander #4, mewtwo #150).

## Selector strategy — and a testability finding 🔎

**The frontend currently exposes no `data-testid` / ARIA hooks.** Elements are
styled `div`s, an ag-grid table and recharts SVGs. So cases select by:

- **accessible text / role** — headings (`Pokemon select`), buttons
  (`⚡ Compare`, `Reset filters`), nav links (`Compare`);
- **placeholder** — the search inputs (`Pikachu...`, `Start typing…`);
- **library DOM** — ag-grid rows `.ag-row` / cells `.ag-cell`, recharts
  `svg.recharts-surface`.

Library-class selectors are brittle (they change with ag-grid/recharts
versions). **Recommendation to the SUT (testability):** add stable
`data-testid` hooks to a handful of anchors — nav container, each filter
input, the results grid + row, the total counter, the selected/target card,
each chart container, the Compare button. This is a legitimate SDET
contribution: *make the product observable to tests.* Each case below notes
the `data-testid` it would ideally use; until they exist, the fallback
selector is used.

## Conventions

- **Case ID:** `E2E-<AREA>-<NN>`. Areas: `NAV`, `SRCH` (select), `CMP`
  (compare), `ANL` (analytics), `SIM` (similar).
- **Priorities:** P0 smoke/core journey · P1 important · P2 secondary · P3
  edge/non-functional. Same P0-P3 scale as the API suite.
- **Kinds:** `smoke`, `journey` (multi-step user flow), `render` (visual
  presence of a component), `negative`, `routing`, `responsive`, `a11y`.

### Waits — web-first, never sleep

The search inputs **debounce ~350 ms**, and grids/charts fill after an async
fetch. Automation uses Playwright **web-first assertions** (`expect(locator)`
auto-retries) and waits on observable outcomes — a row count, a visible card,
a chart `<svg>` — **never** a fixed `sleep`. Cases state the *outcome to wait
for*, not a duration.

### Browser matrix

The P0 journeys run on **chromium, firefox and webkit**; P1+ default to
chromium to keep the run fast. Marked per case as *(matrix)*.

## Structure

| File | Area |
|------|------|
| [01-navigation.md](01-navigation.md) | Layout, nav, client-side routing, deep-link |
| [02-search.md](02-search.md) | Select page: filters, grid, pagination, detail card |
| [03-compare.md](03-compare.md) | Compare: autocomplete, chips, stat table + radar |
| [04-analytics.md](04-analytics.md) | Analytics: grouping, table, charts |
| [05-similar.md](05-similar.md) | Similar: pick target, similar table + radar |
