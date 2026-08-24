# E2E · Accessibility (a11y)

Automated accessibility auditing with **axe-core** (via Playwright) on the
primary user paths. Not a "nice to have" for this project's target market:
the **European Accessibility Act** and **EN 301 549** make WCAG 2.1 AA a
procurement/compliance requirement for a great many EU products, so a suite
that never looks at accessibility has a visible blind spot.

## What automated auditing can and cannot do

axe-core reliably catches *machine-detectable* violations - missing names,
broken label associations, contrast ratios, ARIA misuse. It **cannot** judge
whether a flow is actually usable with a keyboard and a screen reader (focus
order that is technically valid but nonsensical, meaningless alt text, a modal
that traps focus in the wrong place). Roughly a third of WCAG criteria are
machine-checkable at all.

So the scope here is honest: automated audit as a **regression gate**, plus one
explicit keyboard-navigation journey. Full manual audit with assistive
technology is out of scope and stated as such rather than implied.

## Adoption strategy - gate regressions, baseline the backlog

The audit found pre-existing contrast debt across the shared palette
([BUG-007](../../bugs/BUG-007-accessibility-violations.md)). Failing the suite
on 43 known findings would get the check switched off within a week, so:

- **`critical` impact → hard fail, always.**
- **`serious` → fail unless the rule id is in the documented allowlist**
  (`KNOWN_A11Y_ISSUES`), each entry referencing the open bug.
- `moderate` / `minor` → reported, not gated.

Any *new* rule, or a critical regression, breaks the build immediately; the
known debt is burned down separately and its allowlist entry removed.

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-A11Y-01 | Public search page has no critical violations | P1 | a11y |
| E2E-A11Y-02 | Login page has no critical violations | P1 | a11y |
| E2E-A11Y-03 | Checkout page has no critical violations | P2 | a11y |
| E2E-A11Y-04 | Filter controls are programmatically labelled | P1 | a11y |
| E2E-A11Y-05 | Primary flow is keyboard reachable | P2 | a11y |

---

### E2E-A11Y-01 - Public search page · P1 · a11y
**Steps:** open `/`, wait for the grid, run axe-core against the document.
**Expected:** zero violations of `critical` impact; no `serious` violations
outside the allowlist. Regression guard for the unlabelled filter panel
(BUG-007).

### E2E-A11Y-02 - Login page · P1 · a11y
**Steps:** open `/login`, run axe-core.
**Expected:** zero `critical`; no unlisted `serious`. Authentication forms are
the highest-stakes place for a labelling defect - a user who cannot identify
the password field cannot use the product at all.

### E2E-A11Y-03 - Checkout page · P2 · a11y
**Precondition:** logged-in free user (fixture).
**Steps:** open `/checkout`, run axe-core.
**Expected:** zero `critical`; no unlisted `serious`. Payment forms carry the
same reasoning as login, one step further down the funnel.

### E2E-A11Y-04 - Filter controls are programmatically labelled · P1 · a11y
A targeted assertion rather than a whole-page scan, so the specific regression
that BUG-007 fixed is pinned by name and cannot silently come back inside an
allowlisted rule.
**Steps:** open `/`; for each filter control resolve its accessible name.
**Expected:** `filter-name`, `filter-type`, `filter-generation` and
`filter-group` each expose a non-empty accessible name (`<label for>` bound, not
a placeholder).

### E2E-A11Y-05 - Primary flow is keyboard reachable · P2 · a11y
Machine audits do not prove operability, so one journey is driven by keyboard
only.
**Steps:** open `/login`; `Tab` to the email field, type; `Tab` to password,
type; press `Enter`.
**Expected:** the form submits and the session is created - the login flow is
completable without a pointing device (WCAG SC 2.1.1 Keyboard).
