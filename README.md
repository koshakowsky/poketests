# PokéAnalytics - Test Suite (API + E2E)

[![API tests](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml/badge.svg)](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml)
[![Allure report](https://img.shields.io/badge/Allure-report-8A2BE2)](https://koshakowsky.github.io/poketests/allure/)
[![Health dashboard](https://img.shields.io/badge/health-dashboard-4f46e5)](https://koshakowsky.github.io/poketests/)


Test design **and** automation for the
[**pokeanalytics**](https://github.com/koshakowsky/pokeanalytics) system under
test. Two peer suites over one SUT: an **API** suite (pytest + httpx) and an
**E2E** suite (Playwright for Python), both derived from the test-case catalog
in [test-cases/](test-cases/), where every case is annotated with the
design technique it applies, a priority and an expected result.

**At a glance:** 175+ designed cases with **100% catalog→automation
traceability** (every `TC-*` id is executed by a named test) · techniques
applied explicitly - EP / BVA / pairwise / decision tables / error guessing /
state · **auth & authorization** - JWT login, a tier-based RBAC matrix
(401-vs-403) and a fake-checkout state machine (card validation, declines,
idempotency, **concurrency**) · exact, dataset-profile-driven oracles · E2E
journeys over Page Objects on `data-testid` hooks · **contract fuzzing** of
every operation (schemathesis vs the live OpenAPI schema) · **accessibility
gate** (axe-core, WCAG) · CI gate + browser matrix · live health dashboard and
Allure report · **8 defects** found and driven through the full
report→fix→guard cycle.

> **Why a separate repository?** In a product setting a suite that targets a
> single service would live in that service's repo (atomic changes, no
> version skew). It is split out here deliberately, as a standalone
> portfolio artifact; version alignment is handled by the CI checking out a
> pinned ref of the SUT and bringing up its own stack.

---

## Project structure

Co-located project (one SUT → one test repo), **isolated peer suites** (each
owns its deps, fixtures and tests). Everything genuinely shared lives at the
root.

```
poketests/
├── pyproject.toml       dependency groups (PEP 735) + pytest config
├── conftest.py          shared: api client, canary (SUT up + dataset), Allure hook
├── dataset.py           dataset profile - data assumptions in one place
├── fixtures/            shared across suites, registered via pytest_plugins
│   ├── users.py         identity: User, make_user, *_token, premium_api
│   └── billing.py       card/checkout builders (plain helpers, not fixtures)
├── test-cases/          design catalog (api/ + e2e/, mirrors the suites)
├── bugs/  tools/         bug reports · pairwise + dashboard generators
├── api/                 API SUITE  →  pytest api
│   ├── conftest.py      API-only: seed-mode probe & gate, jwt_secret
│   ├── schemas.py       independent response models (shape validation)
│   └── tests/
├── contract/            CONTRACT SUITE  →  pytest contract
│   ├── conftest.py      live-schema loader + premium auth
│   └── tests/           schemathesis fuzzes every operation
└── e2e/                 E2E SUITE  →  pytest e2e
    ├── conftest.py      base_url + Page Object fixtures
    ├── pages/           Page Object Model
    └── tests/
```

---

### Where a fixture lives

One rule, so there is never a second place to look: **anything shared between
suites is a plugin under `fixtures/`; a suite's `conftest.py` holds only what is
unique to that suite.** So identity (users, tokens, authenticated clients) is in
`fixtures/users.py`, and `api/conftest.py` keeps just the seed-mode probe and the
secrets the API suite alone needs.

Test data is built, not duplicated: `fixtures/billing.py` owns the card and
checkout bodies, `dataset.py` owns the data assumptions. A test picks a card
number from `dataset.CARDS` and nothing else needs to know the body shape.

Dependencies follow the same shape. `pyproject.toml` declares one **dependency
group per suite** ([PEP 735](https://peps.python.org/pep-0735/)), each composed
from a `shared` group via `include-group`:

```bash
pip install --group api        # 22 packages
pip install --group contract   # 58 - schemathesis pulls a large tree
pip install --group e2e        # 28 - browsers
```

Keeping them apart is not tidiness, it is install cost: a single merged file
would make every job install 71 packages, and the API job runs twice on each
push. Groups also removed a wrong dependency edge - `contract` used to inherit
`api/requirements.txt` while using nothing from the API suite. No packaging
metadata is involved: this repo is a test suite, not a distributable, so
`pyproject.toml` carries only groups and tool config. Needs **pip >= 25.1**.

---

## Place in the test pyramid

```
        /\
       /E2E\        UI journeys, Playwright - e2e/
      /------\
     /  API   \     <-- integration tests at the HTTP API level - api/
    /----------\        (router + service + DB), fast and stable
   /   Unit     \    pure functions + pytest smoke in the SUT repo
  /--------------\
```

- **Unit (bottom).** Pure logic without HTTP/DB: cosine/magnitude similarity,
  type-advantage calculation, CSV parsing of `types`. Cheap - have many.
- **Contract (between unit and API).** The SUT publishes a live OpenAPI schema
  (`/api/openapi.json`) - the source of truth for the contract. The `contract/`
  suite (schemathesis) fuzzes **every** operation with schema-derived data and
  validates each response against that schema (`not_a_server_error` +
  response/content-type conformance). It found and now guards two robustness
  defects - [BUG-004](bugs/BUG-004-integer-overflow-500.md) (out-of-range int →
  500) and a naive-datetime schema violation. Schema availability is pinned by
  TC-ENV-03.
- **API / integration (middle, our focus).** HTTP requests against a running
  service: status codes, response shape, business rules and validation. Most
  cases in this catalog live here.
- **E2E (top).** UI scenarios (Playwright for Python). Kept minimal -
  end-to-end user journeys only, designed in [test-cases/e2e/](test-cases/e2e/)
  and automated in [e2e/](e2e/).

Distribution rule: anything verifiable at the API level without the UI is
verified here, not in E2E. Anything verifiable by a pure function without a
running service is pushed down to unit.

---

## Test-design techniques applied

| Code | Technique | Where applied |
|------|-----------|---------------|
| **EP** | Equivalence Partitioning | filter values, `group_by`, types, flags, access classes / tiers |
| **BVA** | Boundary Value Analysis | `limit`, `offset`, stat `min/max`, compare id count, `max_pokemon`, password length, card number length, expiry month, CVC length |
| **PW** | Pairwise testing | list filter combinations |
| **DT** | Decision Table | mutually exclusive filters, seed authorization, **RBAC endpoint×role matrix**, **card-validation & checkout-precedence tables** |
| **EG** | Error Guessing | injection into sort_by, duplicate ids, empty/garbage values, token tampering, user enumeration, unknown plan, mass-assignment / privilege escalation, `alg:none`/expired JWT, SQL injection |
| **ST** | State / sequencing | pagination stability, seed → data appears, **register→login→me**, **subscription lifecycle** (checkout → cancel → reactivate), live-tier access |

---

## Priorities

| Priority | Meaning | Criterion |
|----------|---------|-----------|
| **P0** | Critical / smoke | happy paths of core endpoints, key validations; broken → release blocker |
| **P1** | High | important negative cases, boundary values, business rules |
| **P2** | Medium | less likely combinations, extra schema checks |
| **P3** | Low | rare edge cases, non-functional checks |

---

## Conventions

- **Case ID:** `TC-<AREA>-<NN>`. Areas: `HLT` (health), `SEED`, `LIST`
  (list/search), `DET` (detail), `SIM` (similar), `CMP` (compare), `ANL`
  (analytics), `TYP` (types), `ENV` (preconditions), `XC` (cross-cutting),
  `AUTH` (register/login/me), `BILL` (billing/checkout), `RBAC` (access matrix),
  `SEC` (application-layer security).
- **Base prefix:** all routes live under `/api`; case paths are written
  relative to `/api`.
- **Case format:** ID · Title · Priority · Technique · Preconditions (if any) ·
  Request · Expected result (status + body checks).

### Traceability - every designed case is executed

A catalog drifts away from its automation quietly: a case is designed and never
implemented, or an id is renamed on one side only. Rather than assert coverage,
the repo makes it re-runnable:

```bash
python tools/check_traceability.py --strict   # exits 1 on any gap
```

It cross-references every `TC-*` / `E2E-*` id in [test-cases/](test-cases/)
against the ids named in test docstrings, and reports both directions - cases
with no test, and tests citing a case that does not exist.

```
API: 132/132 traced (100%)
E2E:   44/44 traced (100%)
```

The same ids become searchable **Allure tags** (see the `conftest.py` hook), so
a case id links the catalog, the test and the report. Two notes on the edges:
`TC-ENV-*` is implemented as the session canary fixture - a gate, not a case, so
it has no Allure tag by design; and ids are always written in full, never as a
`TC-LIST-03/04/05` shorthand, which would silently register only the first.

### Shared expectations (apply to all cases, not repeated per case)

- Successful responses have `Content-Type: application/json`.
- Successful bodies conform to the endpoint's Pydantic schema (types and
  required fields). Cases list only meaningful checks beyond the schema.
  Enforced once per response type by the automation's *shape tests* via
  **independent test-side models** (`api/schemas.py`, `extra="forbid"`) -
  deliberately not imported from the SUT: validating a response with the
  same models that serialized it would be tautological.
- FastAPI/Pydantic validation errors → **422** with `{"detail": [...]}`.
- Business errors (via `HTTPException`) → the corresponding code with
  `{"detail": "<text>"}`. **Billing** errors instead carry a *structured*
  detail `{"detail": {"error_code": "...", "message": "..."}}` so tests assert
  on a stable `error_code`, not prose (see 11-billing-checkout.md).
- **Auth:** protected routes need `Authorization: Bearer <token>`; missing/
  invalid → 401 (`WWW-Authenticate: Bearer`), insufficient tier → 403.
- GET endpoints are idempotent and do not mutate state.
- **Trailing slash:** routes are declared with a trailing slash
  (`/api/pokemon/`); a slash-less request → `307` redirect (pinned by
  TC-XC-03). The test HTTP client uses canonical paths and does **not**
  silently follow redirects.
- Methods not declared for a route → **405** (checked once, TC-HLT-03; not
  multiplied across endpoints).

### Status-code matrix (quick reference)

| Code | When |
|------|------|
| 200 | successful GET/POST with a result |
| 201 | resource created (register a user) |
| 400 | business rule violated (e.g. compare id count outside 2..6) |
| 401 | **not authenticated** - missing/invalid/expired token; seed: wrong token |
| 402 | payment declined at checkout (`card_declined` / `insufficient_funds`) |
| 403 | **forbidden** - authenticated but tier too low; seed: feature disabled |
| 404 | entity not found (pokemon/type by id); unknown checkout plan |
| 409 | conflict - duplicate email, already subscribed, no active subscription |
| 422 | parameter/body validation error (type/range/enum, card format) |

**401 vs 403** is a deliberate, tested distinction: *no/invalid credentials* →
401, *valid credentials but insufficient tier* → 403 (see
[test-cases/api/12-rbac.md](test-cases/api/12-rbac.md), TC-RBAC-07).

---

## Test environment and data

- **SUT:** a running API (`http://localhost/api` via docker compose, or
  `http://localhost:8000/api` directly).
- **Data precondition:** the DB is seeded with the default set -
  **151 Pokémon (Gen I)**. Cases rely on stable fixtures:

  | id | name | trait |
  |----|------|-------|
  | 1 | bulbasaur | types `grass` + `poison` (dual-type) |
  | 4 | charmander | type `fire` (single-type) |
  | 6 | charizard | `fire` + `flying` |
  | 25 | pikachu | `electric` |
  | 150 | mewtwo | `is_legendary = true`, `psychic` |
  | 151 | mew | `is_mythical = true`, `psychic` |

- **Design consequence:** only Gen I is present in the default seed. So
  `generation=1` → 151 results, while `generation=2..9` → a valid **empty**
  result (`total=0`). This is used as the "valid but empty" class.
- Cases deliberately avoid pinning type counts/averages that would make them
  brittle - they verify structure, invariants and known ids/names instead.
- **Dataset profile.** All data assumptions used by the automation are
  centralized in [dataset.py](dataset.py) (active profile `gen1`, matching
  the SUT fixture `api/fixtures/gen1.json`). Tests take exact oracles from
  the profile instead of hardcoding numbers. The suite owns its data
  (hermetic fixture seeding), which is why exact oracles are the right
  strength; a dataset change means a **new profile file**, not editing
  dozens of tests, and the canary aborts the run if the stand's data does
  not match the active profile.

### Authentication, tiers & test data

- **Auth:** JWT bearer. `POST /api/auth/register` (free user) →
  `POST /api/auth/login` (token) → send `Authorization: Bearer <token>`.
- **Tiers:** `free < premium < admin`. Public endpoints need no auth; analytics,
  `similar` and compare need **premium**; `/admin/users` needs **admin**.
  Full contract in [test-cases/api/12-rbac.md](test-cases/api/12-rbac.md).
- **Seeded admin:** the SUT bootstraps a deterministic admin from env
  (`ADMIN_EMAIL` / `ADMIN_PASSWORD`, defaults `admin@example.com` /
  `admin-password-123`) so admin-tier cases have a known account.
- **Users are created per run:** tests register fresh, unique users (e.g.
  `user+{uuid}@test.io`) rather than relying on fixed accounts - the suite owns
  no reset between tests, and unique emails keep the `409`-duplicate path and
  parallel workers from colliding. A **premium** user is obtained by registering
  then running a successful checkout.
- **Test cards (fake gateway, all Luhn-valid):**

  | Number | Brand | Outcome |
  |--------|-------|---------|
  | `4242 4242 4242 4242` | visa | success |
  | `3782 822463 10005` | amex | success (CVC 4 digits) |
  | `4000 0000 0000 0002` | visa | `402 card_declined` |
  | `4000 0000 0000 9995` | visa | `402 insufficient_funds` |

---

## Catalog structure

| File | Area |
|------|------|
| [test-cases/00-preconditions.md](test-cases/api/00-preconditions.md) | Canary / run entry criteria (fail-fast) |
| [test-cases/01-health.md](test-cases/api/01-health.md) | Health check |
| [test-cases/02-admin-seed.md](test-cases/api/02-admin-seed.md) | Admin: seeding (authorization, bounds) |
| [test-cases/03-pokemon-list-search.md](test-cases/api/03-pokemon-list-search.md) | List/search: filters, sorting, pagination |
| [test-cases/04-pokemon-detail.md](test-cases/api/04-pokemon-detail.md) | Pokemon detail |
| [test-cases/05-pokemon-similar.md](test-cases/api/05-pokemon-similar.md) | Similar Pokemon |
| [test-cases/06-compare.md](test-cases/api/06-compare.md) | Pokemon comparison |
| [test-cases/07-analytics.md](test-cases/api/07-analytics.md) | Analytics |
| [test-cases/08-types.md](test-cases/api/08-types.md) | Types and effectiveness |
| [test-cases/09-cross-cutting.md](test-cases/api/09-cross-cutting.md) | CORS, routing, perf smoke |
| [test-cases/10-auth.md](test-cases/api/10-auth.md) | Auth: register / login / me, JWT |
| [test-cases/11-billing-checkout.md](test-cases/api/11-billing-checkout.md) | Billing & checkout: plans, card validation, declines, idempotency, cancel |
| [test-cases/12-rbac.md](test-cases/api/12-rbac.md) | RBAC: tier access matrix, 401-vs-403 |
| [test-cases/13-security.md](test-cases/api/13-security.md) | Security: mass-assignment, JWT attacks, injection (+ consolidated) |
| [test-cases/e2e/](test-cases/e2e/) | **E2E (UI)** - nav, search, compare, analytics, similar, **auth, checkout** journeys |
| [test-cases/e2e/08-accessibility.md](test-cases/e2e/08-accessibility.md) | **a11y** - axe-core audit gate + keyboard journey |
| [tools/generate_pairwise.py](tools/generate_pairwise.py) | Pairwise set generator (allpairspy) - **imported by** the TC-LIST-27 test, so the documented set and the executed set cannot drift |
| [tools/check_traceability.py](tools/check_traceability.py) | Catalog ↔ automation traceability check (`--strict` for CI) |
| [api/schemas.py](api/schemas.py) | Independent test-side response models (shape validation) |
| [dataset.py](dataset.py) | Dataset profile - centralized data assumptions for exact oracles |
| [bugs/](bugs/) | Bug reports for defects found by this catalog |

The **API** automation lives in [api/](api/) (`pytest api`) and the **E2E**
automation in [e2e/](e2e/) (`pytest e2e`) - see *Running* below.

---

## Running the suites

Both need the SUT up (`docker compose up` in pokeanalytics) so the API - and,
for E2E, the frontend - are reachable. `pyproject.toml` sets `testpaths = api/tests`,
so a bare `pytest` runs the API suite; the `contract` and `e2e` suites are
opt-in via their paths.

### API suite

```bash
pip install --group api
pytest api                    # full API suite (bare `pytest` also works)
pytest api -m p0              # smoke only
pytest api -m restricted      # destructive seed test - isolated stack only
POKETESTS_BASE_URL=http://localhost:8000/api pytest api   # non-default SUT
```

`restricted` tests are excluded by default (`-m "not restricted"` in
`pyproject.toml`); an explicit `-m` on the command line overrides the filter.

**Parallel execution** is supported and used in CI:

```bash
pytest api -n auto            # ~6x faster (22s -> 4s locally)
```

This is not a free speed-up, it is a property of the fixture design: every user
is created with a unique email and nothing is cleaned up between tests, so
workers sharing one SUT cannot collide. Running green under `-n auto` is what
proves that isolation claim rather than asserting it. The `restricted` seed job
stays serial by nature (it wipes and reseeds the database).

### Contract suite

```bash
pip install --group contract
pytest contract               # schemathesis fuzzes every operation
POKETESTS_BASE_URL=http://localhost/api pytest contract
```

Loads the live schema from `/api/openapi.json`, fuzzes each operation with
schema-derived data (authenticated as premium so gated routes are exercised),
and runs `not_a_server_error` + response/content-type conformance.
`status_code_conformance` is intentionally off - FastAPI only auto-documents
200/201 and 422, so it would flag every legitimate business error (401/403/404/
409) as undocumented.

### E2E suite

```bash
pip install --group e2e
playwright install                     # download browser binaries
pytest e2e                             # chromium (default)
pytest e2e --browser firefox --browser webkit   # cross-browser matrix
pytest e2e -n 4                        # parallel (44s -> 12s)
pytest e2e --headed --slowmo 300       # watch it run
```

Both suites run in parallel, but the worker counts differ on purpose. The API
suite uses `-n auto`; E2E is capped at `-n 4`, because a browser worker is far
more expensive than an httpx one and the measured curve flattens past four
(43s serial, 12s at 4, 9s at 8, 10s at 12 - contention starts winning). A fixed
cap also keeps `auto` from launching a browser per core on a bigger runner.
Verified green on chromium, firefox and webkit.

| Env | Default | Purpose |
|-----|---------|---------|
| `POKETESTS_WEB_URL` | `http://localhost` | frontend origin the browser navigates |
| `POKETESTS_BASE_URL` | `http://localhost/api` | API base - used by the shared canary |

E2E uses Page Objects over the SUT's `data-testid` hooks and web-first
Playwright assertions (no sleeps); ag-grid rows / recharts SVGs are selected
`.ag-row` / `svg.recharts-surface` **scoped inside** a `data-testid` container.
The shared root canary applies here too, so "SUT up + Gen I dataset" is a
precondition for the UI as well.

Premium journeys don't re-walk the payment UI every time: a user is registered
and upgraded **through the API**, then its JWT is injected into `localStorage`
before navigation (`browser_login` / `premium_browser` fixtures). Setup goes
through the fastest layer that can do it; the browser is spent on the behaviour
under test.

**Accessibility** ([test-cases/e2e/08-accessibility.md](test-cases/e2e/08-accessibility.md))
runs axe-core over the primary paths. The gate is asymmetric on purpose:
`critical` always fails, `serious` fails only for rules outside a documented
allowlist that points at [BUG-007](bugs/BUG-007-accessibility-violations.md).
Blocking on 43 pre-existing contrast findings would just get the check
disabled - gate the regressions now, burn the backlog down separately. Machine
audits cannot prove operability, so one keyboard-only journey backs them up.

### CI matrix

Seed-endpoint behavior depends on server configuration (`SEED_TOKEN`), so
[.github/workflows/api-tests.yml](.github/workflows/api-tests.yml) treats the
configuration as an explicit axis - three jobs, three stack configs.

Seeding in PR jobs is **hermetic**: the SUT ships a JSON fixture
(`api/fixtures/gen1.json`, exported from a PokeAPI-seeded DB) and seeds from
it synchronously at startup - no external network, "healthy" implies
"dataset ready". That makes the full suite cheap enough to run in **both**
PR configs; only the nightly `seed-run` job exercises the live PokeAPI
integration.

| Job | Stack config | Runs | Trigger |
|-----|--------------|------|---------|
| `api-tests` | no token, fixture-seeded Gen I | full suite (403 branch of the seed DT) | push / PR |
| `seed-auth-tests` | per-run `SEED_TOKEN`, fixture-seeded | full suite (401 branch; the 403 case skips itself) | push / PR |
| `seed-run` | per-run token, empty DB | `-m restricted` (real seeding via live PokeAPI, row 4 of the DT) | manual (`workflow_dispatch`) |

Tests declare their required mode via `seed_disabled`/`seed_enabled` markers;
a session-scoped probe detects the actual stack mode and skips mismatched
tests with a reason. Jobs owning their data disable the dataset canary via
`POKETESTS_SKIP_DATA_CANARY=1` (health canary stays unconditional).

**Pre-merge gate (in the SUT repo).** This workflow tests changes to *this*
repo. A companion workflow lives in the SUT repo
(`pokeanalytics/.github/workflows/pr-gate.yml`): on every PR into
`pokeanalytics` main it checks out this suite at `main` and runs it against
the PR's SUT code. Since it runs in the SUT repo, its status attaches to that
PR automatically and can be made a required check - so a SUT change cannot
merge if it breaks the contract this catalog encodes.

### E2E CI (browser matrix)

[.github/workflows/ui-tests.yml](.github/workflows/ui-tests.yml) runs the E2E
suite against a fresh docker-compose stack across a browser matrix - **full
suite on chromium, P0 smoke on firefox and webkit** (cross-browser on the
critical paths without paying for the whole suite ×3).

Two techniques worth noting:

- **Path filter without breaking the required check.** On a PR the expensive
  browser matrix runs only when E2E-relevant paths changed (`e2e/`,
  `test-cases/e2e/`, shared root files) - detected by a native `git diff`
  step, no third-party action. But the workflow itself always runs, so a
  final **`gate`** job always reports. Make `gate` the required check: it
  passes when the matrix succeeded *or* was legitimately skipped, and fails
  when any browser leg failed. A top-level `on.paths` filter would instead
  leave a required check stuck "pending" on unrelated PRs - the aggregator
  pattern avoids that.
- E2E Allure results are uploaded per browser as artifacts; publishing them
  into the Pages report is a future step (the API suite owns the Pages
  deploy today).

### Dashboard & Allure report

On every push to `main` the `publish-report` job builds and deploys a combined
GitHub Pages site: the **full Allure report** with run-over-run trends under
**<https://koshakowsky.github.io/poketests/allure/>**, and a **project-health
dashboard** at the root (**<https://koshakowsky.github.io/poketests/>**,
generated by [tools/build_dashboard.py](tools/build_dashboard.py)).

The two answer different questions, which is the point of having both. Allure
answers *"did this run pass?"*. The dashboard answers what Allure structurally
cannot, and every number on it is derived at build time rather than typed in:

| Panel | Measured from |
|-------|---------------|
| **Catalog traceability**, overall and per area | the catalog cross-referenced with the test sources |
| **Endpoint coverage** - documented operations actually called | recorded at run time (below) |
| **Test-design techniques** and how heavily each is used | the technique column of the case tables |
| **Tests by layer** (API / Contract / E2E) | the `parentSuite` label added by the Allure hook |
| **Defects**, each tagged with the technique that surfaced it | the `Found by` field of the bug reports |

**Endpoint coverage is measured, not maintained.** Every HTTP client the suites
use is built by [fixtures/endpoint_coverage.py](fixtures/endpoint_coverage.py),
which records the `(method, path)` of each request; the canary contributes the
documented operation list from the SUT's live OpenAPI schema. Concrete paths are
folded back into their template (`/api/pokemon/25` → `/api/pokemon/{pokemon_id}`,
most-literal template wins) and the sets are written next to the Allure results,
one file per process, unioned at build time across suites and xdist workers.

An endpoint added to the SUT and never tested therefore appears on the dashboard
by itself - which a hand-kept checklist of endpoints, all ticked, never would.

Locally:

```bash
pytest api --alluredir=allure-results
allure serve allure-results   # requires Allure CLI (brew install allure)
```

Allure metadata is derived automatically (see `conftest.py`): priority markers
`p0..p3` map to Allure severity, the feature label comes from the test module,
and `TC-*` ids from docstrings become searchable tags - no per-test decorators
to maintain.

---

## Defects found by test design (full lifecycle)

All were found by test design (or fuzzing), documented as bug reports, encoded
as a test against the specification, then **fixed in the SUT** - at which point
the test became a permanent regression guard. This report → fix → guard cycle is
the point.

| Case | Bug report | Defect | Status |
|------|-----------|--------|--------|
| TC-LIST-28 | [BUG-001](bugs/BUG-001-like-wildcard-injection.md) | LIKE-wildcard injection (`name=%` matched everything) | ✅ Fixed - regression guard |
| TC-LIST-29 | [BUG-002](bugs/BUG-002-unstable-pagination-order.md) | Unstable pagination (no tiebreaker on a non-unique sort key) | ✅ Fixed - regression guard |
| TC-BILL-19 | [BUG-003](bugs/BUG-003-cross-user-idempotency-collision.md) | Cross-user idempotency key collision → 500 (global PK) | ✅ Fixed - regression guard |
| contract | [BUG-004](bugs/BUG-004-integer-overflow-500.md) | Out-of-range integer param → 500 (SQLite overflow) | ✅ Fixed - schemathesis guard |
| TC-ANL-03 | [BUG-005](bugs/BUG-005-group-by-enum-not-enforced.md) | `group_by` enum documented but not enforced → silently grouped by the wrong dimension | ✅ Fixed - regression guard |
| TC-DET-03 | [BUG-006](bugs/BUG-006-type-slot-order-ignored.md) | Stored type `slot` ignored → dual types returned reversed | ✅ Fixed - regression guard |
| E2E-A11Y-01/04 | [BUG-007](bugs/BUG-007-accessibility-violations.md) | Unlabelled filter controls (WCAG 4.1.2) - critical for screen readers | ⚠️ Critical fixed; contrast baselined |
| TC-BILL-20 | [BUG-008](bugs/BUG-008-concurrent-checkout-race.md) | Concurrent double-submit → 500 (TOCTOU on subscription insert) | ✅ Fixed - regression guard |

Worth noting **how** each was found - the mix is the point, not the count:
test design against a written spec (001, 002, 005, 006), state/sequencing
design (003), generative contract fuzzing (004), an accessibility audit (007),
and a concurrency case that a sequential test structurally cannot reach (008).
