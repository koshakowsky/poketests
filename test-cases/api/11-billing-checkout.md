# Billing & checkout — `GET /api/billing/plans`, `POST /api/billing/checkout`, `GET /api/billing/subscription`, `POST /api/billing/cancel`

A **fake but realistic** checkout: no external gateway (hermetic, CI-safe), but
a real state machine with card validation, decline simulation and idempotency.
This is the richest DT/BVA surface in the suite.

**Contract:**
- `GET /api/billing/plans` — **public**. List of plans; one paid plan
  `premium` `{id, name, price_cents, currency, interval}`.
- `POST /api/billing/checkout` — **auth required**. Body
  `{plan_id, card:{number, exp_month, exp_year, cvc}, idempotency_key?}`.
  Validates the card, "charges" it, on success upgrades the user to **premium**
  and creates/reactivates a subscription.
- `GET /api/billing/subscription` — **auth required**. Current subscription;
  `status ∈ {none, active, canceled}`.
- `POST /api/billing/cancel` — **auth required**. Cancels an active
  subscription and downgrades to **free**.

**Error bodies** use a stable machine-readable shape: `{"detail":
{"error_code": "...", "message": "..."}}`. Tests assert on `error_code`, never
prose. (Contrast: card fields typed loosely on purpose, so *semantic* errors
come from the app with these codes, not as a generic Pydantic `422`.)

**Test cards** (all Luhn-valid; the outcome is the gateway's decision):

| Number | Brand | Outcome |
|--------|-------|---------|
| `4242 4242 4242 4242` | visa | success |
| `3782 822463 10005` | amex | success (CVC = 4 digits) |
| `4000 0000 0000 0002` | visa | `402 card_declined` |
| `4000 0000 0000 9995` | visa | `402 insufficient_funds` |

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-BILL-01 | Plans are public and well-formed | P0 | EP |
| TC-BILL-02 | Fresh user has no subscription (`status=none`) | P1 | ST |
| TC-BILL-03 | Checkout happy → 200, active, tier→premium | P0 | EP/ST |
| TC-BILL-04 | Checkout — card number validation (Luhn/length) | P0 | BVA/EG |
| TC-BILL-05 | Checkout — expiry validation | P1 | BVA |
| TC-BILL-06 | Checkout — CVC length by brand | P1 | DT/BVA |
| TC-BILL-07 | Checkout — declined cards → 402 | P0 | DT |
| TC-BILL-08 | Checkout — unknown plan → 404 | P1 | EG |
| TC-BILL-09 | Checkout — already active → 409 | P1 | ST/DT |
| TC-BILL-10 | Checkout — decision-table precedence | P1 | DT |
| TC-BILL-11 | Idempotency key replays the same result | P1 | ST |
| TC-BILL-12 | Subscription reflects active details (masked card) | P1 | EP |
| TC-BILL-13 | Cancel active → 200, canceled, tier→free | P0 | ST |
| TC-BILL-14 | Cancel with nothing active → 409 | P1 | ST/DT |
| TC-BILL-15 | Re-subscribe after cancel (reactivation) | P1 | ST |
| TC-BILL-16 | Checkout body validation → 422 | P2 | EG |
| TC-BILL-17 | PAN / CVC never stored or returned in full | P1 | security |
| TC-BILL-18 | Amex happy path (4-digit CVC) | P2 | EP |

---

## Card validation — decision table (DT)

Semantic checks in `billing_cards.validate_card`, in this **fixed order** (one
reason per rejection; tests rely on the specific `error_code`):

| Check | Failing input | → error_code (HTTP) |
|-------|---------------|---------------------|
| digits & length 13–19 | non-digit / <13 / >19 | `invalid_number` (422) |
| Luhn | fails checksum | `invalid_number` (422) |
| exp month 1–12 | 0, 13 | `invalid_expiry` (422) |
| not expired | past year/month | `card_expired` (422) |
| CVC length (3, or 4 for amex) | wrong length / non-digit | `invalid_cvc` (422) |
| charge | decline test card | `card_declined` / `insufficient_funds` (402) |

---

### TC-BILL-01 — Plans are public · P0 · EP
**Request:** `GET /api/billing/plans` (**no** auth)
**Expected:** `200`; a non-empty list; the `premium` plan present with
`{id:"premium", name, price_cents:int>0, currency, interval}`. Public because a
pricing page must render for anonymous visitors.

### TC-BILL-02 — Fresh user has no subscription · P1 · ST
**Precondition:** a newly registered (free) user, logged in.
**Request:** `GET /api/billing/subscription`
**Expected:** `200`; `body.status == "none"`; `plan`, `card_brand`,
`card_last4`, `current_period_end` all `null`. (Absence is `status=none`, not
`404` — one shape the client always renders.)

### TC-BILL-03 — Checkout happy · P0 · EP/ST
**Precondition:** a free user, logged in.
**Request:** `POST /api/billing/checkout`
`{"plan_id":"premium","card":{"number":"4242424242424242","exp_month":12,"exp_year":<future>,"cvc":"123"}}`
**Expected:** `200`; body `{status:"active", plan:"premium",
card_brand:"visa", card_last4:"4242", current_period_end:<~30d ahead>}`.
**Side effects (verify):** `GET /api/auth/me` → `tier == "premium"`;
`GET /api/billing/subscription` → `status == "active"`. The tier change is
readable on the **same** token (tier is read live from the DB).

### TC-BILL-04 — Card number validation · P0 · BVA/EG
Length boundaries around [13, 19] plus the Luhn checksum. Automation builds
Luhn-valid numbers of a target length; use the anchors below.

| Number | Class | Expected |
|--------|-------|----------|
| `424242424242424` (15, non-Luhn) | fails checksum | `422 invalid_number` |
| `4242424242424241` (16, Luhn digit flipped) | fails checksum | `422 invalid_number` |
| `424242424242` (12) | below min length | `422 invalid_number` |
| any Luhn-valid 13-digit (e.g. `4222222222222`) | lower bound | `200` |
| `4242424242424242` (16, Luhn-valid) | mid | `200` |
| any Luhn-valid 19-digit | upper bound | `200` |
| 20-digit | above max length | `422 invalid_number` |
| `"4242-4242-4242-4242"` / spaced | formatting stripped | `200` (normalized) |

### TC-BILL-05 — Expiry validation · P1 · BVA
Card is valid **through** the end of the expiry month. `now` = the run date.

| exp_month / exp_year | Class | Expected |
|----------------------|-------|----------|
| `0` / future | below month bound | `422 invalid_expiry` |
| `13` / future | above month bound | `422 invalid_expiry` |
| `1` / future year | valid month | `200` |
| `12` / future year | valid month | `200` |
| last month (e.g. `now.month-1` / `now.year`) | just expired | `422 card_expired` |
| current month / current year | boundary — still valid | `200` |
| any month / `now.year-1` | past year | `422 card_expired` |

### TC-BILL-06 — CVC length by brand · P1 · DT/BVA
CVC length depends on the brand (amex → 4, others → 3). A cross of
brand × cvc-length.

| Brand (number) | cvc | Expected |
|----------------|-----|----------|
| visa `4242…4242` | `12` (2) | `422 invalid_cvc` |
| visa `4242…4242` | `123` (3) | `200` |
| visa `4242…4242` | `1234` (4) | `422 invalid_cvc` |
| amex `378282246310005` | `123` (3) | `422 invalid_cvc` |
| amex `378282246310005` | `1234` (4) | `200` |
| any | `12a` (non-digit) | `422 invalid_cvc` |

> Amex/visa CVC pairs each need a *fresh* free user (a success upgrades and
> would then hit the `409` guard) — or run the `422` rows against one user and
> the `200` rows against fresh users.

### TC-BILL-07 — Declined cards → 402 · P0 · DT
Card is format-valid; the gateway declines at the charge step.

| Number | Expected |
|--------|----------|
| `4000000000000002` | `402`, `error_code == "card_declined"` |
| `4000000000009995` | `402`, `error_code == "insufficient_funds"` |

**After a decline (verify):** the user stays **free** and `subscription.status`
stays `none` — a failed charge must not upgrade or leave a dangling active sub.

### TC-BILL-08 — Unknown plan → 404 · P1 · EG
**Request:** checkout with `plan_id` = `"gold"` / `""` / `"PREMIUM"` (case).
**Expected:** `404`, `error_code == "unknown_plan"`. Checked **before** the
card (no point charging for a non-existent plan).

### TC-BILL-09 — Already active → 409 · P1 · ST/DT
**Precondition:** a user with an **active** subscription.
**Request:** checkout again (valid card, **no** idempotency key).
**Expected:** `409`, `error_code == "already_subscribed"`. Guards against double
charging; checked **before** card validation.

### TC-BILL-10 — Decision-table precedence · P1 · DT
Multiple conditions can fail at once; the response must reflect the **first**
failing check in precedence order: idempotency-hit → unknown_plan(404) →
already_subscribed(409) → card validation(422) → charge(402) → success(200).

| Scenario | Expected |
|----------|----------|
| active sub **and** invalid card | `409` (409 precedes 422 — active check first) |
| unknown plan **and** invalid card | `404` (plan precedes card) |
| valid state, invalid card **and** would-decline | `422` (format precedes charge) |

### TC-BILL-11 — Idempotency replay · P1 · ST
**Steps:** checkout with `idempotency_key = "k1"` (success) → repeat the exact
request with `"k1"`.
**Expected:** the second call returns the **same** body — including the
identical `current_period_end` — proving the stored response was replayed, not
recomputed. No second "charge", no error. A *different* key against the now-active
sub → `409` (TC-BILL-09).

### TC-BILL-12 — Subscription details (masked card) · P1 · EP
**Precondition:** active subscription bought with visa `4242…4242`.
**Request:** `GET /api/billing/subscription`
**Expected:** `status:"active"`, `plan:"premium"`, `card_brand:"visa"`,
`card_last4:"4242"`, `current_period_end` ~30 days out. Only the **last 4** are
stored — see TC-BILL-17.

### TC-BILL-13 — Cancel active → downgrade · P0 · ST
**Precondition:** active subscription.
**Request:** `POST /api/billing/cancel`
**Expected:** `200`; `status == "canceled"`. **Side effects:** `/me.tier ==
"free"`; premium endpoints now return `403` for this user (see
[12-rbac.md](12-rbac.md), TC-RBAC-08).

### TC-BILL-14 — Cancel with nothing active → 409 · P1 · ST/DT
| State | Expected |
|-------|----------|
| never subscribed | `409`, `no_active_subscription` |
| already canceled | `409`, `no_active_subscription` |

### TC-BILL-15 — Reactivation after cancel · P1 · ST
**Steps:** checkout → cancel → checkout again (valid card).
**Expected:** final checkout `200`; `status == "active"` again; `/me.tier ==
"premium"`. The subscription record is reused (one per user), not duplicated.

### TC-BILL-16 — Checkout body validation → 422 · P2 · EG
Framework-level (before semantic card checks):

| Body | Expected |
|------|----------|
| missing `card` | `422` |
| missing `plan_id` | `422` |
| `exp_month` a string (`"12"`)… | *accepted if coercible; non-coercible → 422* |
| `card` not an object | `422` |
| empty / not JSON | `422` |

### TC-BILL-17 — PAN / CVC not exposed · P1 · security
**Steps:** inspect every billing response body (checkout, subscription).
**Expected:** the full card number never appears — only `card_last4` (4 chars)
and `card_brand`; the **CVC is never stored or returned** in any form. The
test-side `SubscriptionOut` (`extra="forbid"`) fails if a `card_number` / `cvc`
field ever appears.

### TC-BILL-18 — Amex happy path · P2 · EP
**Request:** checkout with amex `378282246310005`, `cvc:"1234"` (4 digits),
future expiry, fresh free user.
**Expected:** `200`; `card_brand == "amex"`, `card_last4 == "0005"`; tier →
premium. Confirms brand detection and the amex-specific CVC length end to end.
