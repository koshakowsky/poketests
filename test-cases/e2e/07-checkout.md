# E2E · Checkout & subscription

The upgrade journey a user actually walks: hit a premium wall → view plans →
pay → get access; and manage/cancel the subscription. Card-validation rules and
decline logic are exhaustively covered at the API layer
([11-billing-checkout.md](../api/11-billing-checkout.md)) — E2E drives only the
**representative** UI paths (one success, one decline, one client-side
rejection) and the resulting state changes a browser can observe.

**Pages / testids:** upgrade wall (`upgrade-prompt`, `view-plans-button`);
`/checkout` (`checkout-page`, `plan-card`, `plan-price`, `card-number`,
`card-brand`, `exp-month`, `exp-year`, `cvc`, `pay-button`, `checkout-error`,
`error-number`, `error-expiry`, `error-cvc`); `/account` (`account-page`,
`account-tier`, `sub-details`, `sub-status`, `cancel-button`,
`resubscribe-button`, `upgrade-cta`).

**Test cards (from the API catalog):** `4242 4242 4242 4242` = success;
`4000 0000 0000 0002` = declined.

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-PAY-01 | Free user hits the premium wall | P0 | journey *(matrix)* |
| E2E-PAY-02 | Full upgrade journey unlocks premium | P0 | journey *(matrix)* |
| E2E-PAY-03 | Declined card shows an error, stays free | P1 | negative |
| E2E-PAY-04 | Client-side card validation blocks submit | P1 | negative |
| E2E-PAY-05 | Cancel subscription re-locks premium | P1 | journey |
| E2E-PAY-06 | Account shows masked subscription details | P2 | render |
| E2E-PAY-07 | Already-premium user on /checkout | P2 | render |

---

### E2E-PAY-01 — Free user hits the premium wall · P0 · journey *(matrix)*
**Precondition:** logged-in **free** user.
**Steps:** navigate to `/analytics`.
**Expected:** the analytics grid does **not** render; `upgrade-prompt` is shown
with a `view-plans-button`. This is the UI form of the API `403` for a free
tier (contrast E2E-AUTH-03, where an *anonymous* user is redirected to login).

### E2E-PAY-02 — Full upgrade journey · P0 · journey *(matrix)*
**Precondition:** logged-in free user.
**Steps:** `/analytics` → click `view-plans-button` → on `/checkout`, fill
`card-number` `4242 4242 4242 4242`, `exp-month` `12`, `exp-year` (a future
year), `cvc` `123` → click `pay-button`.
**Expected:** lands on `/account`; `account-tier` reads `PREMIUM`;
`sub-status` is `active`. Navigating back to `/analytics` now renders the grid
(no upgrade prompt). End-to-end proof that payment unlocks the gated feature.

### E2E-PAY-03 — Declined card · P1 · negative
**Precondition:** logged-in free user on `/checkout`.
**Steps:** fill a valid-format but **declined** card `4000 0000 0000 0002`,
valid expiry and CVC → `pay-button`.
**Expected:** `checkout-error` becomes visible ("Your card was declined."); the
user stays on `/checkout`; tier remains free (returning to `/analytics` still
shows `upgrade-prompt`). A failed charge grants nothing.

### E2E-PAY-04 — Client-side validation blocks submit · P1 · negative
**Steps:** on `/checkout`, enter an obviously invalid card number (e.g. `1234`)
and submit.
**Expected:** an inline `error-number` message appears and **no** network
request is made (the form validates first, mirroring the API's `invalid_number`
without a round-trip). Analogous inline errors: `error-expiry`, `error-cvc`.

### E2E-PAY-05 — Cancel re-locks premium · P1 · journey
**Precondition:** logged-in **premium** user (subscribed).
**Steps:** open `/account`; click `cancel-button`.
**Expected:** `sub-status` becomes `canceled`; `account-tier` becomes `FREE`;
a `resubscribe-button` appears. Navigating to `/analytics` again shows the
`upgrade-prompt`. Mirrors the API downgrade (TC-BILL-13 / TC-RBAC-08).

### E2E-PAY-06 — Account shows masked details · P2 · render
**Precondition:** active subscription bought with `4242…4242`.
**Steps:** open `/account`.
**Expected:** `sub-details` shows plan `premium`, card as `visa •••• 4242`
(brand + last 4 only — never the full number), and a renewal date. Confirms the
masked contract surfaces correctly in the UI.

### E2E-PAY-07 — Already-premium on /checkout · P2 · render
**Precondition:** logged-in premium user.
**Steps:** navigate directly to `/checkout`.
**Expected:** instead of the card form, a "You're on premium" panel with a
`go-account` link — no way to double-pay from the UI (the API also guards this
with `409`, TC-BILL-09).
