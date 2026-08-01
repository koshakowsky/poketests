# E2E · Navigation & layout

The app shell: header, four nav tabs, client-side routing. `BrowserRouter`
means sub-routes are served by the nginx SPA fallback (`try_files … /index.html`)
— worth an explicit deep-link/reload check.

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-NAV-01 | App shell loads (header + 4 tabs) | P0 | smoke *(matrix)* |
| E2E-NAV-02 | Each tab routes to its page | P0 | routing *(matrix)* |
| E2E-NAV-03 | Active tab is highlighted | P2 | render |
| E2E-NAV-04 | Deep-link / reload on a sub-route works | P1 | routing |
| E2E-NAV-05 | No console errors on initial load | P3 | a11y/health |

---

### E2E-NAV-01 — App shell loads · P0 · smoke *(matrix)*
**Steps:** open `/`.
**Expected:** header shows `Poké…Analytics` and the `Gen I` badge; nav shows
four links — **Select, Analytics, Compare, Similar**; the Select page heading
`Pokemon select` is visible.
*testid:* `nav`, `nav-link-{select|analytics|compare|similar}`.

### E2E-NAV-02 — Each tab routes to its page · P0 · routing *(matrix)*
**Steps:** from `/`, click each nav link in turn.
**Expected:** URL and heading match (client-side nav, no full reload):

| Click | URL | Heading |
|-------|-----|---------|
| Analytics | `/analytics` | `Category analysis` |
| Compare | `/compare` | `Compare Pokemon` |
| Similar | `/similar` | `Find a similar Pokemon` |
| Select | `/` | `Pokemon select` |

### E2E-NAV-03 — Active tab highlighted · P2 · render
**Steps:** navigate to `/compare`.
**Expected:** the `Compare` link is styled active (distinct from the others).
Assert via the active-state attribute/class, not exact colors. *(Best served
by an `aria-current="page"` hook — recommend adding it.)*

### E2E-NAV-04 — Deep-link / reload on a sub-route · P1 · routing
**Steps:** navigate directly to `/compare` (fresh load / F5), not via a click.
**Expected:** the Compare page renders (HTTP 200 from the SPA fallback, not a
404). Guards the nginx `try_files … /index.html` rule — a slash-less/unknown
client route must still serve the app.

### E2E-NAV-05 — No console errors on load · P3 · health
**Steps:** open `/` capturing `console` and `pageerror` events.
**Expected:** no `error`-level console messages and no uncaught exceptions
during initial render. Cheap guard against silent runtime breakage.
