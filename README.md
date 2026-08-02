# PokéAnalytics — Test Suite (API + E2E)

[![API tests](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml/badge.svg)](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml)
[![Health dashboard](https://img.shields.io/badge/health-dashboard-4f46e5)](https://koshakowsky.github.io/poketests/)
[![Allure report](https://img.shields.io/badge/Allure-report-8A2BE2)](https://koshakowsky.github.io/poketests/allure/)

Test design **and** automation for the
[**pokeanalytics**](https://github.com/koshakowsky/pokeanalytics) system under
test. Two peer suites over one SUT: an **API** suite (pytest + httpx) and an
**E2E** suite (Playwright for Python), both derived from the test-case catalog
in [test-cases/](test-cases/), where every case is annotated with the
design technique it applies, a priority and an expected result.

**At a glance:** 100+ designed cases with technique traceability (EP / BVA /
pairwise / decision tables / error guessing) · API automation with exact,
dataset-profile-driven oracles · E2E journeys over Page Objects on `data-testid`
hooks · CI gate + browser matrix · a live health dashboard and Allure report ·
2 defects found by test design and driven through the full report→fix→guard
cycle.

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
├── conftest.py          shared: api client, canary (SUT up + dataset), Allure hook
├── dataset.py           dataset profile — data assumptions in one place
├── pytest.ini           shared markers + config
├── test-cases/          design catalog (api/ + e2e/, mirrors the suites)
├── bugs/  tools/         bug reports · pairwise + dashboard generators
├── api/                 API SUITE  →  pytest api
│   ├── requirements.txt
│   ├── conftest.py      API-specific: seed-mode probe & gate
│   ├── schemas.py       independent response models (shape validation)
│   └── tests/
└── e2e/                 E2E SUITE  →  pytest e2e
    ├── requirements.txt
    ├── conftest.py      base_url + Page Object fixtures
    ├── pages/           Page Object Model
    └── tests/
```

---

## Place in the test pyramid

```
        /\
       /E2E\        UI journeys, Playwright — e2e/
      /------\
     /  API   \     <-- integration tests at the HTTP API level — api/
    /----------\        (router + service + DB), fast and stable
   /   Unit     \    pure functions + pytest smoke in the SUT repo
  /--------------\
```

- **Unit (bottom).** Pure logic without HTTP/DB: cosine/magnitude similarity,
  type-advantage calculation, CSV parsing of `types`. Cheap — have many.
- **Contract (between unit and API).** The SUT publishes a live OpenAPI schema
  (`/api/openapi.json`) — the source of truth for the contract. This is the slot
  for generative contract tests (schemathesis): every endpoint is fuzzed with
  schema-derived data and responses are validated against the same schema.
  Schema availability is pinned by TC-ENV-03.
- **API / integration (middle, our focus).** HTTP requests against a running
  service: status codes, response shape, business rules and validation. Most
  cases in this catalog live here.
- **E2E (top).** UI scenarios (Playwright for Python). Kept minimal —
  end-to-end user journeys only, designed in [test-cases/e2e/](test-cases/e2e/)
  and automated in [e2e/](e2e/).

Distribution rule: anything verifiable at the API level without the UI is
verified here, not in E2E. Anything verifiable by a pure function without a
running service is pushed down to unit.

---

## Test-design techniques applied

| Code | Technique | Where applied |
|------|-----------|---------------|
| **EP** | Equivalence Partitioning | filter values, `group_by`, types, flags |
| **BVA** | Boundary Value Analysis | `limit`, `offset`, stat `min/max`, id count in compare, `max_pokemon` |
| **PW** | Pairwise testing | list filter combinations |
| **DT** | Decision Table | mutually exclusive filters (legendary/mythical/regular), seed authorization |
| **EG** | Error Guessing | injection into sort_by, duplicate ids, empty/garbage values |
| **ST** | State / sequencing | pagination (page stability), seed → data appears |

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
  (analytics), `TYP` (types), `ENV` (preconditions), `XC` (cross-cutting).
- **Base prefix:** all routes live under `/api`; case paths are written
  relative to `/api`.
- **Case format:** ID · Title · Priority · Technique · Preconditions (if any) ·
  Request · Expected result (status + body checks).

### Shared expectations (apply to all cases, not repeated per case)

- Successful responses have `Content-Type: application/json`.
- Successful bodies conform to the endpoint's Pydantic schema (types and
  required fields). Cases list only meaningful checks beyond the schema.
  Enforced once per response type by the automation's *shape tests* via
  **independent test-side models** (`api/schemas.py`, `extra="forbid"`) —
  deliberately not imported from the SUT: validating a response with the
  same models that serialized it would be tautological.
- FastAPI/Pydantic validation errors → **422** with `{"detail": [...]}`.
- Business errors (via `HTTPException`) → the corresponding code with
  `{"detail": "<text>"}`.
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
| 400 | business rule violated (e.g. compare id count outside 2..6) |
| 401 | seed: wrong token provided |
| 403 | seed: feature disabled (no token configured) |
| 404 | entity not found (pokemon/type by id) |
| 422 | parameter validation error (type/range/enum/body) |

---

## Test environment and data

- **SUT:** a running API (`http://localhost/api` via docker compose, or
  `http://localhost:8000/api` directly).
- **Data precondition:** the DB is seeded with the default set —
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
  brittle — they verify structure, invariants and known ids/names instead.
- **Dataset profile.** All data assumptions used by the automation are
  centralized in [dataset.py](dataset.py) (active profile `gen1`, matching
  the SUT fixture `api/fixtures/gen1.json`). Tests take exact oracles from
  the profile instead of hardcoding numbers. The suite owns its data
  (hermetic fixture seeding), which is why exact oracles are the right
  strength; a dataset change means a **new profile file**, not editing
  dozens of tests, and the canary aborts the run if the stand's data does
  not match the active profile.

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
| [test-cases/e2e/](test-cases/e2e/) | **E2E (UI)** — nav, search, compare, analytics, similar journeys |
| [tools/generate_pairwise.py](tools/generate_pairwise.py) | Pairwise set generator (allpairspy) for TC-LIST-27 |
| [api/schemas.py](api/schemas.py) | Independent test-side response models (shape validation) |
| [dataset.py](dataset.py) | Dataset profile — centralized data assumptions for exact oracles |
| [bugs/](bugs/) | Bug reports for defects found by this catalog |

The **API** automation lives in [api/](api/) (`pytest api`) and the **E2E**
automation in [e2e/](e2e/) (`pytest e2e`) — see *Running* below.

---

## Running the suites

Both need the SUT up (`docker compose up` in pokeanalytics) so the API — and,
for E2E, the frontend — are reachable. `pytest.ini` sets `testpaths = api/tests`,
so a bare `pytest` runs the API suite; E2E is opt-in via the `e2e` path.

### API suite

```bash
pip install -r api/requirements.txt
pytest api                    # full API suite (bare `pytest` also works)
pytest api -m p0              # smoke only
pytest api -m restricted      # destructive seed test — isolated stack only
POKETESTS_BASE_URL=http://localhost:8000/api pytest api   # non-default SUT
```

`restricted` tests are excluded by default (`-m "not restricted"` in
`pytest.ini`); an explicit `-m` on the command line overrides the filter.

### E2E suite

```bash
pip install -r e2e/requirements.txt
playwright install                     # download browser binaries
pytest e2e                             # chromium (default)
pytest e2e --browser firefox --browser webkit   # cross-browser matrix
pytest e2e --headed --slowmo 300       # watch it run
```

| Env | Default | Purpose |
|-----|---------|---------|
| `POKETESTS_WEB_URL` | `http://localhost` | frontend origin the browser navigates |
| `POKETESTS_BASE_URL` | `http://localhost/api` | API base — used by the shared canary |

E2E uses Page Objects over the SUT's `data-testid` hooks and web-first
Playwright assertions (no sleeps); ag-grid rows / recharts SVGs are selected
`.ag-row` / `svg.recharts-surface` **scoped inside** a `data-testid` container.
The shared root canary applies here too, so "SUT up + Gen I dataset" is a
precondition for the UI as well.

### CI matrix

Seed-endpoint behavior depends on server configuration (`SEED_TOKEN`), so
[.github/workflows/api-tests.yml](.github/workflows/api-tests.yml) treats the
configuration as an explicit axis — three jobs, three stack configs.

Seeding in PR jobs is **hermetic**: the SUT ships a JSON fixture
(`api/fixtures/gen1.json`, exported from a PokeAPI-seeded DB) and seeds from
it synchronously at startup — no external network, "healthy" implies
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
PR automatically and can be made a required check — so a SUT change cannot
merge if it breaks the contract this catalog encodes.

### Dashboard & Allure report

On every push to `main` the `publish-report` job builds and deploys a combined
GitHub Pages site: a **project-health dashboard** at the root
(**<https://koshakowsky.github.io/poketests/>** — pass rate, priority
breakdown, pyramid, endpoint coverage and bug lifecycle, generated from the
run's Allure results by [tools/build_dashboard.py](tools/build_dashboard.py)),
and the **full Allure report** with run-over-run trends under
**<https://koshakowsky.github.io/poketests/allure/>**. Locally:

```bash
pytest api --alluredir=allure-results
allure serve allure-results   # requires Allure CLI (brew install allure)
```

Allure metadata is derived automatically (see `conftest.py`): priority markers
`p0..p3` map to Allure severity, the feature label comes from the test module,
and `TC-*` ids from docstrings become searchable tags — no per-test decorators
to maintain.

---

## Defects found by test design (full lifecycle)

Both were found by test design, documented as bug reports, encoded as
`xfail(strict)` tests against the specification, then **fixed in the SUT** —
at which point the `xfail` came off and each test became a permanent
regression guard. This report → fix → guard cycle is the point.

| Case | Bug report | Defect | Status |
|------|-----------|--------|--------|
| TC-LIST-28 | [BUG-001](bugs/BUG-001-like-wildcard-injection.md) | LIKE-wildcard injection (`name=%` matched everything) | ✅ Fixed — regression guard |
| TC-LIST-29 | [BUG-002](bugs/BUG-002-unstable-pagination-order.md) | Unstable pagination (no tiebreaker on a non-unique sort key) | ✅ Fixed — regression guard |
