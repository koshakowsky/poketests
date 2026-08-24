# BUG-007 - accessibility: unlabelled form controls (WCAG 4.1.2 / 1.3.1)

| Field | Value |
|-------|-------|
| **Status** | **Partially fixed** - critical violations fixed; `color-contrast` accepted as a known issue (see below) |
| **Severity** | **Major** (critical impact: the search filters are unusable with a screen reader) |
| **Priority** | P1 - the EU market treats accessibility as a compliance requirement, not a nicety |
| **Component** | Frontend - Select page filter controls; app-wide colour palette |
| **Environment** | pokeanalytics frontend, axe-core via Playwright, chromium |
| **Found by** | Accessibility audit (axe-core), cases [E2E-A11Y-01..03](../test-cases/e2e/08-accessibility.md) |
| **Automated as** | `e2e/tests/test_a11y.py` (regression guard with an explicit known-issue allowlist) |

## Summary

An axe-core audit of the running SPA found violations at three impact levels.
The **critical** ones make the whole filter panel inoperable for assistive
technology: every filter rendered its caption as a plain `<span>`, so the visual
label had no programmatic association with its control. A screen reader
announced the selects and sliders as unnamed.

| Rule | Impact | Nodes (before) | Where |
|------|--------|----------------|-------|
| `label` | critical | 4 | Select page - name input, stat range sliders |
| `select-name` | critical | 3 | Select page - Type / Generation / Group |
| `color-contrast` | serious | 41 (`/`), 2 (`/login`) | app-wide muted text on light backgrounds |
| `empty-table-header` | minor | 2 | ag-grid selection column headers |

Relevant standards: **WCAG 2.1 SC 4.1.2 Name, Role, Value** and
**SC 1.3.1 Info and Relationships** (labels); **SC 1.4.3 Contrast (Minimum)**.

## Steps to reproduce

```bash
pytest e2e/tests/test_a11y.py           # or, manually:
```
Open `/`, run axe-core against the document, inspect `violations`.

## Expected result

No `critical` or `serious` violations on the primary user paths.

## Actual result (before the fix)

7 critical violations across the filter panel; 43 serious contrast violations.

## Root cause

[`frontend/src/pages/SearchPage.tsx`](../../pokeanalytics/frontend/src/pages/SearchPage.tsx)
styled captions as `<span style={label}>…</span>`. A `<span>` carries no
labelling semantics - visually it reads as a label, programmatically it is
unrelated text. `placeholder` is likewise not a substitute for a label.

## Fix (applied - critical only)

Captions became real labels bound to their controls:

```tsx
<label style={label} htmlFor="filter-generation">Generation</label>
<select id="filter-generation" …>
```

Applied to the name input, all three selects and the four range sliders.
Styling is unchanged - only the element and the association. After the fix both
`label` and `select-name` report **zero** nodes.

## Known issue - `color-contrast` (accepted, not fixed)

The 43 contrast failures come from the muted greys in the shared design tokens
(`colors.gray400/gray500` on light surfaces), not from a single component.
Fixing them means re-tuning the palette app-wide, which is a design decision
rather than a defect fix, and touches every screen.

Deliberately handled as a **baselined known issue**: the automated check gates
`critical` unconditionally and allows only the rule ids listed in
`KNOWN_A11Y_ISSUES`, each pointing back here. Any *new* rule - or a critical
regression - fails the build, while the pre-existing contrast debt does not
block delivery. Removing the entry from the allowlist is the follow-up task
once the palette is re-tuned.

> This is the standard way to adopt accessibility testing on an existing
> product: gate the regressions immediately, burn down the backlog separately.
> Failing the suite on 43 pre-existing findings would only get the check
> disabled.

## Verification (done)

`test_a11y.py` asserts zero `critical` violations on `/`, `/login` and
`/checkout`, and no `serious` violations outside the documented allowlist.
