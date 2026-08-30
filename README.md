# PokéAnalytics - Test Suite

[![API tests](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml/badge.svg)](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml)
[![Allure report](https://img.shields.io/badge/Allure-report-8A2BE2)](https://koshakowsky.github.io/poketests/allure/)
[![Health dashboard](https://img.shields.io/badge/health-dashboard-4f46e5)](https://koshakowsky.github.io/poketests/)

Test design **and** automation for the
[**pokeanalytics**](https://github.com/koshakowsky/pokeanalytics) system under
test. Three peer suites over one SUT - **API** (pytest + httpx), **contract**
(schemathesis vs the live OpenAPI schema) and **E2E** (Playwright for Python).
API and E2E are derived from the catalog in [test-cases/](test-cases/), where
every case carries the design technique it applies, a priority and an expected
result.

**At a glance:** 176 designed cases, **100% traced** to named tests · EP / BVA /
pairwise / decision tables / error guessing / state · JWT auth, a tier RBAC
matrix (401-vs-403) and a fake-checkout state machine (card validation,
declines, idempotency, **concurrency**) · exact oracles from a dataset profile ·
**contract fuzzing** of every operation · **accessibility gate** (axe-core) ·
pre-merge CI gate + browser matrix · **8 defects** driven through
report → fix → guard.

> **Why a separate repository?** In a product setting a suite targeting one
> service belongs in that service's repo - atomic changes, no version skew. It
> is split out here deliberately, as a standalone portfolio artifact; version
> alignment is handled by CI checking out a pinned ref of the SUT and bringing
> up its own stack.

---

## Project structure

```
poketests/
├── pyproject.toml       dependency groups (PEP 735) + pytest config
├── conftest.py          api client, canary (SUT up + dataset), Allure hook
├── dataset.py           dataset profile - data assumptions in one place
├── fixtures/            shared across suites, registered via pytest_plugins
│   ├── users.py             identity: User, make_user, *_token, premium_api
│   ├── billing.py           card/checkout builders (plain helpers)
│   └── endpoint_coverage.py recording HTTP client - feeds the dashboard
├── test-cases/          design catalog (api/ + e2e/, mirrors the suites)
├── bugs/  tools/        bug reports · pairwise, traceability, dashboard
├── api/                 API SUITE       →  pytest api
│   ├── conftest.py          seed-mode probe & gate, jwt_secret
│   ├── schemas.py           independent response models
│   └── tests/
├── contract/            CONTRACT SUITE  →  pytest contract
└── e2e/                 E2E SUITE       →  pytest e2e
    ├── pages/               Page Object Model
    └── tests/
```

**Where a fixture lives** - one rule, so there is never a second place to look:
anything shared between suites is a plugin under `fixtures/`; a suite's
`conftest.py` holds only what is unique to it. Test data is built, not
duplicated - `fixtures/billing.py` owns the checkout bodies, `dataset.py` owns
the data assumptions.

Dependencies follow the same shape: one **dependency group per suite**
([PEP 735](https://peps.python.org/pep-0735/)), composed from a `shared` group
via `include-group`.

```bash
pip install --group api        # 22 packages
pip install --group contract   # 58 - schemathesis pulls a large tree
pip install --group e2e        # 28 - browsers
```

Keeping them apart is install cost, not tidiness: one merged file would make
every job install 71 packages, and the API job runs twice per push. Groups also
removed a wrong edge - `contract` used to inherit `api/requirements.txt` while
using nothing from the API suite. Needs **pip >= 25.1**.

---

## Place in the test pyramid

```
        /\
       /E2E\        UI journeys, Playwright - e2e/
      /------\
     /  API   \     <-- integration at the HTTP level - api/
    /----------\        (router + service + DB), fast and stable
   /   Unit     \    pure functions, in the SUT repo
  /--------------\
```

- **Unit (bottom).** The card-validation core (`billing_cards.py`) is free of
  the app and the database, so its 43 tests import it directly and run in
  0.01 s. Extracting it was a test-design decision: the API cases then prove
  wiring, not arithmetic.
- **Contract.** The SUT publishes a live OpenAPI schema - the source of truth.
  The `contract/` suite fuzzes **every** operation with schema-derived data and
  validates each response against that schema. It found and now guards
  [BUG-004](bugs/BUG-004-integer-overflow-500.md) (out-of-range int → 500) and a
  naive-datetime schema violation.
- **API / integration (our focus).** Status codes, response shape, business
  rules, validation. Most of the catalog lives here.
- **E2E (top).** Kept minimal - end-to-end journeys only.

Distribution rule: anything verifiable at the API level without the UI is
verified there, not in E2E; anything verifiable by a pure function without a
running service is pushed down to unit.

---

## Test design

| Code | Technique | Where applied |
|------|-----------|---------------|
| **EP** | Equivalence Partitioning | filter values, `group_by`, types, flags, access classes / tiers |
| **BVA** | Boundary Value Analysis | `limit`, `offset`, stat `min/max`, compare id count, password length, card number length, expiry month, CVC length |
| **PW** | Pairwise | list filter combinations |
| **DT** | Decision Table | mutually exclusive filters, seed authorization, **RBAC endpoint×role matrix**, **card-validation & checkout-precedence tables** |
| **EG** | Error Guessing | injection into `sort_by`, duplicate ids, garbage values, token tampering, user enumeration, mass-assignment, `alg:none`/expired JWT, SQL injection |
| **ST** | State / sequencing | pagination stability, seed → data appears, register→login→me, **subscription lifecycle**, live-tier access |

| Priority | Meaning |
|----------|---------|
| **P0** | happy paths of core endpoints, key validations; broken → release blocker |
| **P1** | important negative cases, boundary values, business rules |
| **P2** | less likely combinations, extra schema checks |
| **P3** | rare edge cases, non-functional checks |

**Case ID:** `TC-<AREA>-<NN>` (`E2E-<AREA>-<NN>` for UI). Areas: `HLT`, `SEED`,
`LIST`, `DET`, `SIM`, `CMP`, `ANL`, `TYP`, `ENV`, `XC`, `AUTH`, `BILL`, `RBAC`,
`SEC`. All routes live under `/api`; case paths are written relative to it.

### Traceability - every designed case is executed

A catalog drifts from its automation quietly: a case is designed and never
implemented, or an id is renamed on one side only. Rather than assert coverage,
the repo makes it re-runnable:

```bash
python tools/check_traceability.py --strict   # exits 1 on any gap; runs in CI
```

```
API: 132/132 traced (100%)
E2E:  44/44 traced (100%)
```

The same ids become searchable **Allure tags**, so a case id links the catalog,
the test and the report. Two edges: `TC-ENV-*` is the session canary - a gate,
not a case, so it carries no tag by design; and ids are always written in full,
never as a `TC-LIST-03/04/05` shorthand, which would register only the first.

### Shared expectations

Applied to all cases, so they are not repeated per case:

- Successful bodies conform to the endpoint's schema, enforced by *shape tests*
  against **independent test-side models** (`api/schemas.py`, `extra="forbid"`).
  Deliberately not imported from the SUT: validating a response with the models
  that serialized it would be tautological. `extra="forbid"` is also how a
  leaked field (a password hash) gets caught.
- Validation errors → **422** with `{"detail": [...]}`. Business errors → the
  matching code with `{"detail": "<text>"}`; **billing** errors carry a
  structured `{"detail": {"error_code": ..., "message": ...}}` so tests assert a
  stable code, not prose.
- Protected routes need `Authorization: Bearer <token>`; missing/invalid → 401,
  insufficient tier → 403.
- Routes are declared with a trailing slash; a slash-less request → `307`
  (pinned by TC-XC-03). The client uses canonical paths and does not silently
  follow redirects. Undeclared methods → **405** (checked once, TC-HLT-03).

| Code | When |
|------|------|
| 200 / 201 | success / user created |
| 400 | business rule violated (compare id count outside 2..6) |
| 401 | **not authenticated** - missing/invalid/expired token; seed: wrong token |
| 402 | payment declined (`card_declined` / `insufficient_funds`) |
| 403 | **forbidden** - authenticated, tier too low; seed: feature disabled |
| 404 | entity not found; unknown checkout plan |
| 409 | duplicate email, already subscribed, no active subscription |
| 422 | parameter/body validation error (type/range/enum, card format) |

**401 vs 403** is a deliberate, tested distinction - see
[12-rbac.md](test-cases/api/12-rbac.md), TC-RBAC-07.

---

## Environment and data

**SUT:** a running API at `http://localhost/api` (docker compose). The DB is
seeded with the default set - **151 Pokémon (Gen I)**. Stable fixtures cases
rely on:

| id | name | trait |
|----|------|-------|
| 1 | bulbasaur | `grass` + `poison` (dual-type) |
| 4 | charmander | `fire` (single-type) |
| 6 | charizard | `fire` + `flying` |
| 25 | pikachu | `electric` |
| 150 | mewtwo | `is_legendary`, `psychic` |
| 151 | mew | `is_mythical`, `psychic` |

Only Gen I is present, so `generation=1` → 151 results while `generation=2..9`
→ a valid **empty** result - used as the "valid but empty" class.

All data assumptions live in [dataset.py](dataset.py) (profile `gen1`, matching
the SUT fixture `api/fixtures/gen1.json`); tests take exact oracles from the
profile instead of hardcoding numbers. The suite owns its data (hermetic
seeding), which is why exact oracles are the right strength: a dataset change
means a **new profile**, not editing dozens of tests, and the canary aborts the
run if the stand's data does not match.

**Auth and tiers.** `free < premium < admin`. Public endpoints need no auth;
analytics, `similar` and compare need premium; `/admin/users` needs admin. The
SUT bootstraps a deterministic admin from env so admin cases have a known
account. Tests register fresh unique users (`user+{uuid}@test.io`) rather than
sharing fixed accounts - there is no reset between tests, and unique emails keep
the `409`-duplicate path and parallel workers from colliding. A premium user is
made by registering, then running a successful checkout.

**Test cards** (fake gateway, all Luhn-valid):

| Number | Brand | Outcome |
|--------|-------|---------|
| `4242 4242 4242 4242` | visa | success |
| `3782 822463 10005` | amex | success (CVC 4 digits) |
| `4000 0000 0000 0002` | visa | `402 card_declined` |
| `4000 0000 0000 9995` | visa | `402 insufficient_funds` |

| Env | Default | Purpose |
|-----|---------|---------|
| `POKETESTS_BASE_URL` | `http://localhost/api` | API base |
| `POKETESTS_WEB_URL` | `http://localhost` | frontend origin for E2E |
| `POKETESTS_JWT_SECRET` | *(unset)* | must match the SUT's, so TC-SEC-03 can forge an expired token; the cases skip without it |
| `POKETESTS_SEED_TOKEN` | *(unset)* | enables the `restricted` seed test |

---

## Running

All three suites need the SUT up (`docker compose up` in pokeanalytics).
`pyproject.toml` sets `testpaths = api/tests`, so a bare `pytest` runs the API
suite; `contract` and `e2e` are opt-in by path.

```bash
pip install --group api
pytest api                    # full API suite
pytest api -m p0              # smoke only
pytest api -n auto            # ~6x faster (22s -> 4s locally)
pytest api -m restricted      # destructive seed test - isolated stack only

pip install --group contract
pytest contract               # schemathesis fuzzes every operation

pip install --group e2e && playwright install
pytest e2e                                      # chromium
pytest e2e --browser firefox --browser webkit   # cross-browser
pytest e2e -n 4                                 # parallel (43s -> 12s)
pytest e2e --headed --slowmo 300                # watch it run
```

`restricted` tests are excluded by default (`-m "not restricted"` in
`pyproject.toml`); an explicit `-m` overrides that.

**Parallelism is a property of the fixture design, not a flag.** Every user is
created with a unique email and nothing is cleaned up, so workers sharing one
SUT cannot collide - running green under `-n auto` is what *proves* that
isolation rather than asserting it. E2E is capped at `-n 4` because a browser
worker costs far more than an httpx one and the measured curve flattens past
four (43s serial, 12s at 4, 9s at 8, 10s at 12 - contention starts winning); a
fixed cap also stops `auto` launching a browser per core on a bigger runner.
The `restricted` seed job stays serial by nature - it wipes and reseeds the DB.

**Contract suite.** Loads the live schema, fuzzes each operation with
schema-derived data (authenticated as premium so gated routes are reached), and
runs `not_a_server_error` + response/content-type conformance.
`status_code_conformance` is intentionally off: FastAPI auto-documents only
200/201 and 422, so it would flag every legitimate business error as
undocumented.

**E2E** uses Page Objects over the SUT's `data-testid` hooks and web-first
assertions (no sleeps). Premium journeys don't re-walk the payment UI: a user is
registered and upgraded **through the API**, then its JWT is injected into
`localStorage` before navigation. Setup goes through the fastest layer that can
do it; the browser is spent on the behaviour under test.

**Accessibility** ([08-accessibility.md](test-cases/e2e/08-accessibility.md))
runs axe-core over the primary paths. The gate is asymmetric on purpose:
`critical` always fails, `serious` fails only outside a documented allowlist
pointing at [BUG-007](bugs/BUG-007-accessibility-violations.md). Blocking on 43
pre-existing contrast findings would just get the check disabled - gate the
regressions now, burn the backlog down separately. Machine audits cannot prove
operability, so one keyboard-only journey backs them up.

---

## CI

Seed-endpoint behaviour depends on server configuration, so
[api-tests.yml](.github/workflows/api-tests.yml) treats that configuration as an
explicit axis - three jobs, three stack configs.

| Job | Stack config | Runs | Trigger |
|-----|--------------|------|---------|
| `api-tests` | no token, fixture-seeded Gen I | full suite (403 branch of the seed DT) | push / PR |
| `seed-auth-tests` | per-run `SEED_TOKEN`, fixture-seeded | full suite (401 branch) | push / PR |
| `seed-run` | per-run token, empty DB | `-m restricted` (real seeding via live PokeAPI) | manual |

Seeding in PR jobs is **hermetic**: the SUT ships a JSON fixture and seeds from
it synchronously at startup - no external network, "healthy" implies "dataset
ready". Tests declare their required mode via `seed_disabled`/`seed_enabled`
markers; a session-scoped probe detects the actual mode and skips mismatched
tests with a reason.

[ui-tests.yml](.github/workflows/ui-tests.yml) runs E2E against a fresh stack
across a browser matrix - **full suite on chromium, P0 smoke on firefox and
webkit**. On a PR the expensive matrix runs only when E2E-relevant paths
changed, but the workflow always runs so a final **`gate`** job always reports:
it passes when the matrix succeeded *or* was legitimately skipped, and fails
when any leg failed. Make `gate` the required check - a top-level `on.paths`
filter would instead leave a required check stuck pending on unrelated PRs.

**Pre-merge gate (in the SUT repo).** A companion workflow,
`pokeanalytics/.github/workflows/pr-gate.yml`, runs on every PR into the SUT:
it checks this suite out at `main` and runs it
against the PR's code, so its status attaches to that PR and can be required. A
SUT change cannot merge if it breaks the contract this catalog encodes.

---

## Dashboard & Allure report

Every push to `main` deploys a combined Pages site: the **Allure report** with
run-over-run trends at
**<https://koshakowsky.github.io/poketests/allure/>**, and a **health
dashboard** at the root (**<https://koshakowsky.github.io/poketests/>**, built
by [tools/build_dashboard.py](tools/build_dashboard.py)). E2E results are
downloaded from the matching `ui-tests` run and merged in, so the report covers
all three layers.

The two answer different questions. Allure answers *"did this run pass?"*. The
dashboard answers what Allure structurally cannot, and every number on it is
derived at build time rather than typed in:

| Panel | Measured from |
|-------|---------------|
| Catalog traceability, overall and per area | the catalog cross-referenced with the test sources |
| Endpoint coverage - documented operations actually called | recorded at run time (below) |
| Test-design techniques and how heavily each is used | the technique column of the case tables |
| Tests by layer (API / Contract / E2E) | the `parentSuite` label added by the Allure hook |
| Defects, each tagged with the technique that surfaced it | the `Found by` field of the bug reports |

**Endpoint coverage is measured, not maintained.** Every HTTP client the suites
use is built by [fixtures/endpoint_coverage.py](fixtures/endpoint_coverage.py),
which records the `(method, path)` of each request; the canary contributes the
documented operations from the live OpenAPI schema. Concrete paths are folded
back into their template (`/api/pokemon/25` → `/api/pokemon/{pokemon_id}`,
most-literal wins) and the sets are unioned at build time across suites and
xdist workers. An endpoint added to the SUT and never tested therefore appears
on the dashboard by itself - which a hand-kept checklist, all ticked, never
would.

Allure metadata is derived automatically (see `conftest.py`): `p0..p3` markers
map to severity, the feature label comes from the test module, and `TC-*` ids
become searchable tags - no per-test decorators to maintain. Locally:

```bash
pytest api --alluredir=allure-results
allure serve allure-results
```

---

## Defects found by test design

Each was found by design or fuzzing, documented as a report, encoded as a test
against the specification, then **fixed in the SUT** - at which point the test
became a permanent regression guard. That report → fix → guard cycle is the
point.

| Case | Bug report | Defect | Status |
|------|-----------|--------|--------|
| TC-LIST-28 | [BUG-001](bugs/BUG-001-like-wildcard-injection.md) | LIKE-wildcard injection (`name=%` matched everything) | ✅ Fixed - guarded |
| TC-LIST-29 | [BUG-002](bugs/BUG-002-unstable-pagination-order.md) | Unstable pagination (no tiebreaker on a non-unique sort key) | ✅ Fixed - guarded |
| TC-BILL-19 | [BUG-003](bugs/BUG-003-cross-user-idempotency-collision.md) | Cross-user idempotency key collision → 500 | ✅ Fixed - guarded |
| contract | [BUG-004](bugs/BUG-004-integer-overflow-500.md) | Out-of-range integer param → 500 (SQLite overflow) | ✅ Fixed - schemathesis guard |
| TC-ANL-03 | [BUG-005](bugs/BUG-005-group-by-enum-not-enforced.md) | `group_by` enum documented but not enforced → silently grouped by the wrong dimension | ✅ Fixed - guarded |
| TC-DET-03 | [BUG-006](bugs/BUG-006-type-slot-order-ignored.md) | Stored type `slot` ignored → dual types returned reversed | ✅ Fixed - guarded |
| E2E-A11Y-01/04 | [BUG-007](bugs/BUG-007-accessibility-violations.md) | Unlabelled filter controls (WCAG 4.1.2) | ⚠️ Critical fixed; contrast baselined |
| TC-BILL-20 | [BUG-008](bugs/BUG-008-concurrent-checkout-race.md) | Concurrent double-submit → 500 (TOCTOU on subscription insert) | ✅ Fixed - guarded |

Worth noting **how** each was found - the mix is the point, not the count: test
design against a written spec (001, 002, 005, 006), state/sequencing design
(003), generative contract fuzzing (004), an accessibility audit (007), and a
concurrency case a sequential test structurally cannot reach (008).
