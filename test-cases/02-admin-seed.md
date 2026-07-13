# Admin / Seed — `POST /api/admin/seed`

Starts background seeding from PokéAPI. Protected by a token in the
`X-Seed-Token` header. Behavior depends on the server-side `SEED_TOKEN` env:

- `SEED_TOKEN` not set → the endpoint is **disabled** (403 for everyone);
- `SEED_TOKEN` set → a matching header is required, otherwise 401.

`max_pokemon` parameter — `Query(151, ge=1, le=1025)`.

> ⚠️ **Automation caution.** A successful call launches real background
> seeding (hundreds of requests to the external PokéAPI, DB overwrite). The
> positive case TC-SEED-05 is marked *restricted* — run it only in an isolated
> environment, never in the shared run. Authorization/validation cases
> (401/403/422) are safe: seeding is never reached.

---

## Authorization — decision table (DT)

The decision is driven by two conditions: whether `SEED_TOKEN` is configured
on the server and what `X-Seed-Token` arrives in the request.

| # | `SEED_TOKEN` on server | `X-Seed-Token` header | Expected code | Case |
|---|------------------------|------------------------|---------------|------|
| 1 | not set | (any / absent) | **403** disabled | TC-SEED-01 |
| 1b | set to `""` (empty) | (any / absent) | **403** disabled | TC-SEED-08 |
| 2 | set | absent | **401** invalid | TC-SEED-02 |
| 3 | set | wrong | **401** invalid | TC-SEED-03 |
| 3b | set | present but `""` (empty value) | **401** invalid | TC-SEED-07 |
| 4 | set | correct | **200** + background task started | TC-SEED-05 |

---

## Automation architecture (config-dependent tests)

Rows of this table require **different server configurations**, which a test
cannot change at runtime. The automation therefore treats the configuration
as an explicit axis:

- tests **declare** the required mode via markers `seed_disabled` /
  `seed_enabled`;
- the actual mode is **probed** once per session (a safe unauthenticated
  `POST`: 403 → disabled, 401 → enabled) and mismatched tests are skipped
  with a reason;
- the CI matrix brings the stack up in both modes (see
  `.github/workflows/api-tests.yml`) and runs the **full suite in both** —
  hermetic fixture seeding makes that cheap; mismatched-mode tests skip via
  the probe. The destructive row 4 runs only in the manual/nightly
  `seed-run` job (`restricted` marker, empty DB, data canary disabled via
  `POKETESTS_SKIP_DATA_CANARY=1`) — the single place that exercises the live
  PokeAPI integration;
- the secret reaches the tests via `POKETESTS_SEED_TOKEN` — generated per CI
  run and passed to both the stack and the suite, never stored.

---

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-SEED-01 | Seeding disabled without a server token → 403 | P0 | DT |
| TC-SEED-02 | Token configured, header absent → 401 | P1 | DT |
| TC-SEED-03 | Token configured, header wrong → 401 | P1 | DT |
| TC-SEED-04 | `max_pokemon` out of range → 422 | P1 | BVA |
| TC-SEED-05 | Correct token starts seeding → 200 *(restricted)* | P1 | DT/ST |
| TC-SEED-06 | Non-numeric `max_pokemon` → 422 | P2 | EG |
| TC-SEED-07 | Empty `X-Seed-Token` value → 401 | P1 | DT/EG |
| TC-SEED-08 | Server `SEED_TOKEN=""` behaves as disabled → 403 | P2 | DT/EG |

---

### TC-SEED-01 — Seeding disabled without a server token · P0 · DT
**Precondition:** `SEED_TOKEN` is not set on the server (default configuration).
**Request:** `POST /api/admin/seed`
**Expected:** status `403`, `body.detail == "Seeding is disabled"`.

### TC-SEED-02 — Token configured, header absent · P1 · DT
**Precondition:** server has `SEED_TOKEN=<secret>`.
**Request:** `POST /api/admin/seed` (no `X-Seed-Token`)
**Expected:** status `401`, `body.detail == "Invalid seed token"`.

### TC-SEED-03 — Token configured, header wrong · P1 · DT
**Precondition:** server has `SEED_TOKEN=<secret>`.
**Request:** `POST /api/admin/seed` with `X-Seed-Token: wrong`
**Expected:** status `401`, `body.detail == "Invalid seed token"`.

### TC-SEED-04 — `max_pokemon` out of range · P1 · BVA
Bounds: `ge=1, le=1025`. Checked at the edges.

| Sub-case | `max_pokemon` | Class | Expected |
|----------|---------------|-------|----------|
| a | 0 | below lower bound | 422 |
| b | 1 | lower bound (valid) | passes validation (then 401/403 by token) |
| c | 1025 | upper bound (valid) | passes validation |
| d | 1026 | above upper bound | 422 |
| e | -5 | negative | 422 |

> For b/c the point is that the parameter passes validation, not that seeding
> starts: with no token configured the response is 403/401, which is expected.

### TC-SEED-05 — Correct token starts seeding · P1 · DT/ST · *restricted*
**Precondition:** isolated environment, `SEED_TOKEN=<secret>`, DB may be wiped.
**Request:** `POST /api/admin/seed?max_pokemon=5` with `X-Seed-Token: <secret>`
**Expected:**
- status `200`, `body.status == "background_task_started"`,
  `body.message` contains "5";
- **ST check (with a wait):** within a reasonable timeout
  `GET /api/pokemon/?limit=5` returns ≥1 record (the background task ran).

### TC-SEED-06 — Non-numeric `max_pokemon` · P2 · EG
**Request:** `POST /api/admin/seed?max_pokemon=abc`
**Expected:** status `422` (parameter type coercion error).

### TC-SEED-07 — Empty `X-Seed-Token` value · P1 · DT/EG
**Precondition:** server has `SEED_TOKEN=<secret>`.
**Request:** `POST /api/admin/seed` with `X-Seed-Token:` (header present,
empty value)
**Expected:** status `401`. An empty value is a distinct class from an
absent header — the classic hole in `if token: ...`-style checks.

### TC-SEED-08 — Server `SEED_TOKEN=""` behaves as disabled · P2 · DT/EG
**Precondition:** server started with `SEED_TOKEN=` (empty string) — note
this is the **default** of the compose stack (`SEED_TOKEN: ${SEED_TOKEN:-}`).
**Request:** `POST /api/admin/seed` with any/no header
**Expected:** status `403` ("Seeding is disabled"). Pins the
falsy-empty-string behavior: a future "improvement" to an `is not None`
check would silently enable the endpoint with an empty password.
