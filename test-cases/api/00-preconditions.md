# Preconditions / Canary — run entry criteria

The catalog pins deterministic oracles of the default seed (`total==151`,
chansey HP=250, 4 legendaries, etc.). If a precondition does not hold, **the
whole run is invalid**, and dozens of red tests would be noise hiding the real
cause. Canary checks therefore run **before** the main suite and stop the run
on failure (fail-fast).

**Automation:** a session-scoped pytest fixture; on failure — `pytest.exit()`
with a clear message ("SUT unreachable" / "dataset does not match the default
seed — run aborted").

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-ENV-01 | SUT is reachable (health) | P0 | ST |
| TC-ENV-02 | Dataset canary: default Gen I seed | P0 | ST |
| TC-ENV-03 | OpenAPI schema available (contract source) | P1 | ST |

---

### TC-ENV-01 — SUT is reachable · P0
**Request:** `GET /api/health`
**Expected:** `200`, `body.status == "ok"`. Otherwise abort the run: the SUT
is down or failed its healthcheck.

### TC-ENV-02 — Dataset canary · P0
**Request:** `GET /api/pokemon/?limit=1`
**Expected:** `200`, **`total == 151`**. Otherwise abort the run: the DB is
empty (seeding did not finish) or seeded with a non-default set — the
catalog's oracles do not apply.

> **Conditional:** jobs that manage the data themselves (e.g. the restricted
> seed-run job, which starts from an intentionally empty DB) disable this
> check via `POKETESTS_SKIP_DATA_CANARY=1`. Rationale: the canary protects
> oracles that assume the default seed; such jobs have no those oracles. The
> health canary (TC-ENV-01) is unconditional always.

### TC-ENV-03 — OpenAPI schema available · P1
**Request:** `GET /api/openapi.json`
**Expected:** `200` **and** `Content-Type: application/json` **and** the body
parses as JSON with a `paths` key containing `/api/pokemon/`,
`/api/compare/`, `/api/analytics/categories`. The live schema is the source
of truth for the contract layer (see README, contract/schemathesis layer).

> A bare `200` is not a sufficient oracle here: behind the nginx reverse
> proxy the SPA fallback answers unknown paths with `200` + index.html, so a
> misrouted schema would false-pass a status-only check.
