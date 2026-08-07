# RBAC — role/tier-based access control matrix

Authorization spans every endpoint, so it is specified once here rather than
duplicated per file. The auth **endpoints** are in [10-auth.md](10-auth.md);
this file covers **who may call what**.

## Model

Tiers are ranked: **`free (0) < premium (1) < admin (2)`**. A route requires a
*minimum* tier; a request satisfies it when the user's rank is ≥ required.

Endpoints fall into three access classes:

| Class | Min tier | Endpoints |
|-------|----------|-----------|
| **public** | none | `GET /health`, `GET /pokemon/` (+ `/search`), `GET /pokemon/{id}`, `GET /types/`, `GET /billing/plans`, `POST /auth/register`, `POST /auth/login` |
| **authenticated** | any logged-in | `GET /auth/me`, `POST /billing/checkout`, `GET /billing/subscription`, `POST /billing/cancel` |
| **premium** | premium | `GET /analytics/*`, `GET /pokemon/{id}/similar`, `POST /compare/` |
| **admin** | admin | `GET /admin/users` |

## The central oracle — 401 vs 403

The distinction is the whole point of RBAC and is tested explicitly:

- **401 Unauthorized** — *no / invalid credentials*. The server can't identify
  the caller (missing header, malformed/expired/tampered token).
- **403 Forbidden** — *identified, but not allowed*. A valid token whose tier is
  below the requirement.

Getting these backwards (403 for anonymous, or 401 for a logged-in free user) is
a classic auth bug; TC-RBAC-07 pins the split.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-RBAC-01 | Public endpoints reachable anonymously | P0 | EP |
| TC-RBAC-02 | Premium endpoints anonymous → 401 | P0 | EP |
| TC-RBAC-03 | Premium endpoints as free → 403 | P0 | EP |
| TC-RBAC-04 | Premium endpoints as premium → 200 | P0 | EP |
| TC-RBAC-05 | Premium endpoints as admin → 200 (rank ≥) | P1 | EP/DT |
| TC-RBAC-06 | Admin endpoint — full role row | P1 | DT |
| TC-RBAC-07 | 401-vs-403 distinction is correct | P0 | DT |
| TC-RBAC-08 | Tier is read live (upgrade/cancel take effect) | P1 | ST |
| TC-RBAC-09 | Endpoint × role access matrix | P1 | DT |

---

### TC-RBAC-01 — Public endpoints, anonymous · P0 · EP
**Request (no `Authorization`):** each public endpoint.
**Expected:** `200` (or the endpoint's own non-auth code — e.g.
`GET /pokemon/999999` → `404`). Access control never intervenes; auth is not
required. Pokémon **list and detail are intentionally public** — only the
*analytical* features are gated.

### TC-RBAC-02 — Premium, anonymous → 401 · P0 · EP
**Request (no token):** `GET /analytics/type-distribution`,
`GET /pokemon/1/similar`, `POST /compare/` `{"pokemon_ids":[1,4]}`.
**Expected:** `401` for each; `WWW-Authenticate: Bearer` present. Not 403 —
the caller is unidentified.

### TC-RBAC-03 — Premium as free → 403 · P0 · EP
**Precondition:** a logged-in **free** user.
**Request:** the same three premium endpoints, with the free user's token.
**Expected:** `403`; `body.detail == "Requires premium tier"`. Identified but
under-privileged.

### TC-RBAC-04 — Premium as premium → 200 · P0 · EP
**Precondition:** a **premium** user (via checkout, TC-BILL-03).
**Request:** the three premium endpoints.
**Expected:** `200` — the feature is unlocked.

### TC-RBAC-05 — Premium as admin → 200 · P1 · EP/DT
**Precondition:** the seeded **admin** user.
**Request:** the three premium endpoints.
**Expected:** `200`. Admin outranks premium (`require_tier` is a *minimum*, not
equality) — a higher tier is never locked out of a lower requirement.

### TC-RBAC-06 — Admin endpoint, full role row · P1 · DT
`GET /api/admin/users` requires the admin tier.

| Caller | Expected |
|--------|----------|
| anonymous (no token) | `401` |
| free | `403` |
| premium | `403` |
| admin | `200`, a list of `{id, email, tier}` |

### TC-RBAC-07 — 401-vs-403 distinction · P0 · DT
The crux, isolated on one representative premium endpoint
(`GET /analytics/type-distribution`):

| Credentials | Expected | Meaning |
|-------------|----------|---------|
| none | `401` | unidentified |
| malformed/garbage token | `401` | unidentified |
| valid token, **free** tier | `403` | identified, under-privileged |
| valid token, **premium**/admin | `200` | allowed |

### TC-RBAC-08 — Tier read live from DB · P1 · ST
The tier is **not** baked into the token — it is read from the DB per request,
so tier changes take effect on the **same** token without re-login.

**Steps (one token throughout):**
1. free user → premium endpoint → `403`;
2. `POST /billing/checkout` (success) → premium endpoint → `200`;
3. `POST /billing/cancel` → premium endpoint → `403` again.

**Expected:** access follows the DB tier immediately at each step. Cross-refs
TC-BILL-03 / TC-BILL-13.

### TC-RBAC-09 — Endpoint × role access matrix · P1 · DT
The consolidated authorization contract. Rows = representative endpoints,
columns = caller identity. Cell = expected status.

| Endpoint | anonymous | free | premium | admin |
|----------|-----------|------|---------|-------|
| `GET /health` | 200 | 200 | 200 | 200 |
| `GET /pokemon/` | 200 | 200 | 200 | 200 |
| `GET /pokemon/{id}` | 200 | 200 | 200 | 200 |
| `GET /types/` | 200 | 200 | 200 | 200 |
| `GET /billing/plans` | 200 | 200 | 200 | 200 |
| `GET /auth/me` | 401 | 200 | 200 | 200 |
| `GET /billing/subscription` | 401 | 200 | 200 | 200 |
| `POST /billing/checkout` | 401 | 200* | 409† | 409† |
| `GET /analytics/*` | 401 | 403 | 200 | 200 |
| `GET /pokemon/{id}/similar` | 401 | 403 | 200 | 200 |
| `POST /compare/` | 401 | 403 | 200 | 200 |
| `GET /admin/users` | 401 | 403 | 403 | 200 |

> \* free + valid card → 200 and upgrades to premium.
> † premium/admin already have an active sub (or are above it) → `409
> already_subscribed`. The **authorization** result is "allowed" (not 401/403);
> the 409 is a business-state conflict, verified in [11-billing-checkout.md](11-billing-checkout.md).
> The matrix asserts the *access class* per cell; business codes (404/409/422)
> are owned by the endpoint's own catalog file.
