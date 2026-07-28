# PokéAnalytics — API Test Catalog

[![API tests](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml/badge.svg)](https://github.com/koshakowsky/poketests/actions/workflows/api-tests.yml)
[![Allure report](https://img.shields.io/badge/Allure-report-8A2BE2)](https://koshakowsky.github.io/poketests/)

Test-case catalog and automation for the
[**pokeanalytics**](https://github.com/koshakowsky/pokeanalytics) REST API
(the companion system under test). The catalog is the **test design** layer:
every case is annotated with the test-design technique it applies, a priority
and an expected result. The automation layer (pytest + httpx) is derived
from this catalog.

**At a glance:** 80+ designed cases with technique traceability (EP / BVA /
pairwise / decision tables / error guessing) · 50 automated checks with
exact, dataset-profile-driven oracles · a 3-job CI matrix over server
configurations · 2 documented defects found by test design, encoded as
strict `xfail` until fixed.

> **Why a separate repository?** In a product setting a suite that targets a
> single service would live in that service's repo (atomic changes, no
> version skew). It is split out here deliberately, as a standalone
> portfolio artifact; version alignment is handled by the CI checking out a
> pinned ref of the SUT and bringing up its own stack.

---

## Place in the test pyramid

```
        /\
       /E2E\        UI, Playwright (separate layer, not here)
      /------\
     /  API   \     <-- THIS CATALOG: integration tests at the HTTP API level
    /----------\        (router + service + DB), fast and stable
   /   Unit     \    pytest smoke in api/tests + pure functions (similarity, type advantage)
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
- **E2E (top).** UI scenarios (Playwright). Kept minimal — end-to-end user
  journeys only. Not described in this catalog.

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
  **independent test-side models** (`schemas.py`, `extra="forbid"`) —
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
| [test-cases/00-preconditions.md](test-cases/00-preconditions.md) | Canary / run entry criteria (fail-fast) |
| [test-cases/01-health.md](test-cases/01-health.md) | Health check |
| [test-cases/02-admin-seed.md](test-cases/02-admin-seed.md) | Admin: seeding (authorization, bounds) |
| [test-cases/03-pokemon-list-search.md](test-cases/03-pokemon-list-search.md) | List/search: filters, sorting, pagination |
| [test-cases/04-pokemon-detail.md](test-cases/04-pokemon-detail.md) | Pokemon detail |
| [test-cases/05-pokemon-similar.md](test-cases/05-pokemon-similar.md) | Similar Pokemon |
| [test-cases/06-compare.md](test-cases/06-compare.md) | Pokemon comparison |
| [test-cases/07-analytics.md](test-cases/07-analytics.md) | Analytics |
| [test-cases/08-types.md](test-cases/08-types.md) | Types and effectiveness |
| [test-cases/09-cross-cutting.md](test-cases/09-cross-cutting.md) | CORS, routing, perf smoke |
| [tools/generate_pairwise.py](tools/generate_pairwise.py) | Pairwise set generator (allpairspy) for TC-LIST-27 |
| [schemas.py](schemas.py) | Independent test-side response models (shape validation) |
| [dataset.py](dataset.py) | Dataset profile — centralized data assumptions for exact oracles |
| [bugs/](bugs/) | Bug reports for defects found by this catalog |

---

## Running the suite

```bash
pip install -r requirements.txt
pytest                        # full run (SUT must be up, see conftest.py)
pytest -m p0                  # smoke only
pytest -m restricted          # destructive seed test — isolated stack only
POKETESTS_BASE_URL=http://localhost:8000/api pytest   # non-default SUT
```

`restricted` tests are excluded by default (`-m "not restricted"` in
`pytest.ini`); an explicit `-m` on the command line overrides the filter.

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

### Allure report

The latest report is published to GitHub Pages on every push to `main`:
**<https://koshakowsky.github.io/poketests/>** (the `publish-report` job runs
`allure generate` on the main suite's results and deploys them). Locally:

```bash
pytest --alluredir=allure-results
allure serve allure-results   # requires Allure CLI (brew install allure)
```

Allure metadata is derived automatically (see `conftest.py`): priority markers
`p0..p3` map to Allure severity, the feature label comes from the test module,
and `TC-*` ids from docstrings become searchable tags — no per-test decorators
to maintain.

---

## Known defect candidates (bug hunting)

Cases where the **specified** behavior diverges from the **actual** one.
Policy: the test encodes the specification and is automated as `xfail`
referencing the bug report; once fixed, the `xfail` marker comes off and the
test becomes a regression guard.

| Case | Bug report | Defect | Essence |
|------|-----------|--------|---------|
| TC-LIST-28 | [BUG-001](bugs/BUG-001-like-wildcard-injection.md) | LIKE-wildcard injection | `name=%` / `name=_` are not escaped → the filter returns everything instead of a literal match |
| TC-LIST-29 | [BUG-002](bugs/BUG-002-unstable-pagination-order.md) | Unstable pagination | no secondary tiebreaker when sorting by a non-unique key → tie order is not defined by the contract |
