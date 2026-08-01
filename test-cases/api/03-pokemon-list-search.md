# Pokemon List / Search — `GET /api/pokemon/` and `GET /api/pokemon/search`

Both endpoints share the same query parameters and logic (`/search` is an
alias). Default sorting: `sort_by=stat_total`, `sort_order=desc`, `limit=50`,
`offset=0`.

**Parameters and validation:**

| Parameter | Type / rule | Semantics |
|-----------|-------------|-----------|
| `name` | str, opt. | substring, case-insensitive (`ILIKE %name%`) |
| `types` | CSV of strings | **AND**: the pokemon must have **all** listed types |
| `generation` | int | exact match |
| `is_legendary` / `is_mythical` | bool | exact match |
| `min/max_stat_total`, `min/max_hp`, `min/max_attack`, `min/max_defense`, `min/max_speed` | int | range (`>=` / `<=`) |
| `habitat`, `color` | str | exact match |
| `sort_by` | str, **allowlist** | outside the list → silent fallback to `id` (NOT an error) |
| `sort_order` | `^(asc|desc)$` | otherwise **422** |
| `limit` | int, `ge=1, le=100` | otherwise **422** |
| `offset` | int, `ge=0` | otherwise **422** |

> ⚠️ `PokemonListItem` does **not** expose `habitat`/`color` in the list
> schema. The `color`/`habitat` filters work server-side but cannot be
> verified in the list body — cross-check via `GET /api/pokemon/{id}`
> (detail). Also, `sort_by` accepts `sp_attack`/`sp_defense` although there
> are no min/max filters for them (API asymmetry).

**Response:** `PaginatedResponse { items[], total, limit, offset, has_more }`.

---

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-LIST-01 | Default listing | P0 | EP |
| TC-LIST-02 | `/search` behaves like `/` (parity) | P1 | EP |
| TC-LIST-03 | `name` filter — substring | P1 | EP |
| TC-LIST-04 | `name` is case-insensitive | P1 | EG |
| TC-LIST-05 | `name` with no matches → empty | P1 | EP (valid-empty) |
| TC-LIST-06 | `types` filter (single type) | P0 | EP |
| TC-LIST-07 | `types` AND semantics (two types) | P1 | DT |
| TC-LIST-08 | `types` unknown type → empty | P2 | EP |
| TC-LIST-09 | `generation=1` → the whole set | P1 | EP |
| TC-LIST-10 | `generation=2` → empty (only Gen I seeded) | P1 | EP (valid-empty) |
| TC-LIST-11 | Non-numeric `generation` → 422 | P2 | EG |
| TC-LIST-12 | `is_legendary=true` | P1 | EP |
| TC-LIST-13 | `is_mythical=true` | P2 | EP |
| TC-LIST-14 | `is_legendary=false` excludes legendaries | P2 | EP |
| TC-LIST-15 | Non-bool `is_legendary` → 422 | P3 | EG |
| TC-LIST-16 | Stat ranges (boundaries) | P1 | BVA |
| TC-LIST-17 | Contradictory range (min>max) → empty | P2 | EG |
| TC-LIST-18 | `color` filters (cross-check via detail) | P2 | EP |
| TC-LIST-19 | Sort by `stat_total` desc | P1 | EP |
| TC-LIST-20 | Sort by `id` asc | P1 | EP |
| TC-LIST-21 | Invalid `sort_by` → fallback to id, no 500 | P0 | EG |
| TC-LIST-22 | Invalid `sort_order` → 422 | P1 | BVA |
| TC-LIST-23 | `limit` boundaries | P0 | BVA |
| TC-LIST-24 | `offset` boundaries and past-the-end | P1 | BVA |
| TC-LIST-25 | `has_more` correctness at the boundary | P1 | BVA |
| TC-LIST-26 | Page stability (no dupes/gaps) | P1 | ST (regression) |
| TC-LIST-27 | Pairwise filter combinations (allpairspy) | P2 | PW |
| TC-LIST-28 | LIKE wildcards in `name` (`%`, `_`) | P1 | EG · 🐞 bug-candidate |
| TC-LIST-29 | Pagination with a non-unique sort key | P2 | ST/EG · 🐞 bug-candidate |
| TC-LIST-30 | Empty and whitespace-padded `types` | P2 | EG |

---

### TC-LIST-01 — Default listing · P0 · EP
**Request:** `GET /api/pokemon/`
**Expected:** `200`; `limit==50`, `offset==0`, `total==151`, `len(items)==50`,
`has_more==true`; every item contains `id,name,types,stat_total,hp,...`;
**default order** — `stat_total` descending: `items[0]` is mewtwo (680), the
`stat_total` sequence is non-increasing.

### TC-LIST-02 — `/search` and `/` parity · P1 · EP
**Request:** `GET /api/pokemon/search` and `GET /api/pokemon/`
**Expected:** with identical parameters `total` matches and the items
structure is identical (same default sorting and field set).

### TC-LIST-03 — `name` substring · P1 · EP
**Request:** `GET /api/pokemon/?name=char`
**Expected:** `200`; the result contains `charmander`, `charmeleon`,
`charizard`; every `name` contains the substring `char`.

### TC-LIST-04 — `name` is case-insensitive · P1 · EG
**Request:** `GET /api/pokemon/?name=PIKA`
**Expected:** `200`; `pikachu` is present.

### TC-LIST-05 — `name` with no matches · P1 · EP (valid empty class)
**Request:** `GET /api/pokemon/?name=zzzzz`
**Expected:** `200`; `total==0`, `items==[]`, `has_more==false`.

### TC-LIST-06 — `types` single type · P0 · EP
**Request:** `GET /api/pokemon/?types=fire`
**Expected:** `200`; `total>0`; every item has `fire` among `types`
(charmander id=4 is present).

### TC-LIST-07 — `types` AND semantics · P1 · DT
A two-type filter must return only pokemon that have **both** types.

| Request | Expected |
|---------|----------|
| `?types=grass,poison` | bulbasaur (id=1) present; every item has both `grass` and `poison`; pure-`grass` or pure-`poison` pokemon are absent |
| `?types=fire,water` | `total==0` (no fire+water pokemon in Gen I) |

### TC-LIST-08 — Unknown `types` value · P2 · EP
**Request:** `GET /api/pokemon/?types=plasma`
**Expected:** `200`; `total==0` (the request is valid, the value is outside
the domain).

### TC-LIST-09 — `generation=1` · P1 · EP
**Request:** `GET /api/pokemon/?generation=1&limit=100`
**Expected:** `200`; `total==151`.

### TC-LIST-10 — `generation=2` empty · P1 · EP (valid empty class)
**Request:** `GET /api/pokemon/?generation=2`
**Expected:** `200`; `total==0` (only Gen I in the default seed).

### TC-LIST-11 — Non-numeric `generation` · P2 · EG
**Request:** `GET /api/pokemon/?generation=abc`
**Expected:** `422`.

### TC-LIST-12 — `is_legendary=true` · P1 · EP
**Request:** `GET /api/pokemon/?is_legendary=true`
**Expected:** `200`; **`total==4`** — exactly articuno (144), zapdos (145),
moltres (146), mewtwo (150); all have `is_legendary==true`; mew (151) is
**absent** — mythical ≠ legendary.

### TC-LIST-13 — `is_mythical=true` · P2 · EP
**Request:** `GET /api/pokemon/?is_mythical=true`
**Expected:** `200`; **`total==1`** — only mew (id=151).

### TC-LIST-14 — `is_legendary=false` · P2 · EP
**Request:** `GET /api/pokemon/?is_legendary=false&limit=100`
**Expected:** `200`; **`total==147`** (151 − 4 legendaries); mewtwo (150) is
absent; bulbasaur (1) and mew (151, mythical-but-not-legendary) are present.

### TC-LIST-15 — Non-bool `is_legendary` · P3 · EG
**Request:** `GET /api/pokemon/?is_legendary=maybe`
**Expected:** `422`.

### TC-LIST-16 — Stat ranges (boundaries) · P1 · BVA
Classes anchored to known values. Bulbasaur `stat_total=318`; mewtwo
`stat_total=680` (Gen I maximum).

| Sub-case | Request | Expected |
|----------|---------|----------|
| a | `?min_stat_total=680` | `total==1` — only mewtwo (680 is the maximum); exact boundary |
| b | `?min_stat_total=681` | `total==0` (above the maximum) |
| c | `?max_stat_total=0` | `total==0` (below the minimum) |
| d | `?min_attack=0` | no filtering effect (everything passes) — `total==151` |
| e | `?min_hp=250` | `total==1` — exactly chansey (id=113, HP=250 — Gen I maximum); exact boundary |
| f | `?min_hp=251` | `total==0` (just past the maximum) |

> Invariant for non-empty results: every item satisfies all supplied
> `min/max` constraints (e.g. `item.stat_total >= min_stat_total`).

### TC-LIST-17 — Contradictory range · P2 · EG
**Request:** `GET /api/pokemon/?min_stat_total=600&max_stat_total=300`
**Expected:** `200`; `total==0` (min>max is a valid empty result, not an
error).

### TC-LIST-18 — `color` filters (cross-check) · P2 · EP
**Request:** `GET /api/pokemon/?color=red&limit=100`
**Expected:** `200`; `total>0`. Since `color` is not in the list schema, take
any `item.id` from the result, request `GET /api/pokemon/{id}` and assert
`detail.color=="red"`.

### TC-LIST-19 — Sort by `stat_total` desc · P1 · EP
**Request:** `GET /api/pokemon/?sort_by=stat_total&sort_order=desc&limit=100`
**Expected:** `200`; the `stat_total` sequence is non-increasing; the first
item is mewtwo (680).

### TC-LIST-20 — Sort by `id` asc · P1 · EP
**Request:** `GET /api/pokemon/?sort_by=id&sort_order=asc`
**Expected:** `200`; `items[0].id==1`; `id` strictly increases.

### TC-LIST-21 — Invalid `sort_by` → fallback, no 500 · P0 · EG
Regression case: the server-side allowlist must neutralize arbitrary
attributes.

| Request | Expected |
|---------|----------|
| `?sort_by=__class__` | `200` (NOT 500); order identical to `id` |
| `?sort_by=nonexistent_col` | `200`; fallback to `id` |
| `?sort_by=height_m` (property, not a column) | `200`; fallback to `id` |

### TC-LIST-22 — Invalid `sort_order` · P1 · BVA/EP
| Request | Expected |
|---------|----------|
| `?sort_order=asc` | `200` |
| `?sort_order=desc` | `200` |
| `?sort_order=up` | `422` (does not match the pattern) |
| `?sort_order=ASC` | `422` (case does not match the pattern) |

### TC-LIST-23 — `limit` boundaries · P0 · BVA
Rule: `ge=1, le=100`.

| `limit` | Class | Expected |
|---------|-------|----------|
| 0 | below bound | `422` |
| 1 | lower bound | `200`, `len(items)==1` |
| 50 | typical | `200`, `len(items)==50` |
| 100 | upper bound | `200`, `len(items)==100` |
| 101 | above bound | `422` |
| -1 | negative | `422` |
| abc | non-numeric | `422` |

### TC-LIST-24 — `offset` boundaries and tail · P1 · BVA
Rule: `ge=0`. `total=151`.

| `offset` (+`limit`) | Expected |
|---------------------|----------|
| `offset=0` | `200`, first page |
| `offset=-1` | `422` |
| `offset=150&limit=50` | `200`, `len(items)==1`, `has_more==false` |
| `offset=1000` | `200`, `items==[]`, `total==151`, `has_more==false` |

### TC-LIST-25 — `has_more` correctness at the boundary · P1 · BVA
`has_more == (offset + limit) < total`, `total=151`.

| Request | Expected |
|---------|----------|
| `offset=0&limit=100` | `has_more==true` (100<151) |
| `offset=100&limit=50` | `len(items)==50` (items 101–150), `has_more==true` (150<151) |
| `offset=101&limit=50` | `len(items)==50` (items 102–151), `has_more==false` (151<151 = false) — exact boundary |

> The "partial last page" case (`offset=150&limit=50` → 1 item,
> `has_more==false`) is covered by TC-LIST-24 and not duplicated here.

### TC-LIST-26 — Page stability · P1 · ST · *regression*
Guards against the row-multiplication pagination bug (joinedload →
selectinload).
**Steps:** with fixed sorting `sort_by=id&sort_order=asc`
1. page 1: `?limit=50&offset=0` — collect `ids1`;
2. page 2: `?limit=50&offset=50` — collect `ids2`;
3. page 3: `?limit=50&offset=100` — collect `ids3`.
**Expected:**
- `len(ids1)==50`, `len(ids2)==50`, `len(ids3)==50` (full pages, no
  shortfall caused by dual-type pokemon);
- the sets `ids1, ids2, ids3` are pairwise disjoint;
- `|ids1 ∪ ids2 ∪ ids3| == 150` (no cross-page duplicates).

### TC-LIST-27 — Pairwise filter combinations · P2 · PW
The set is **generated by `allpairspy`** — script
[tools/generate_pairwise.py](../tools/generate_pairwise.py) (regenerate with
`python tools/generate_pairwise.py`). All-pairs coverage is guaranteed by the
generator.

Factors and values:

- **types**: `—` / `fire` / `water`
- **generation**: `—` / `1`
- **is_legendary**: `—` / `true` / `false`
- **sort_by**: `stat_total` / `id`
- **sort_order**: `asc` / `desc`
- **limit**: `1` / `100`

**Constraints applied during generation:**
1. `generation=2` is excluded from the matrix: with the default seed (Gen I
   only) it always yields an empty result, on which the verification-bearing
   factors `sort_by/sort_order/limit` are unobservable. The "valid-empty"
   class is covered by dedicated cases TC-LIST-08/10 — pairwise does not
   spend coverage on it.
2. `types=water` × `is_legendary=true` is excluded via filter: Gen I has no
   water-type legendaries — another empty class.

| # | types | gen | legendary | sort_by | order | limit | Expected (beyond shared invariants) |
|---|-------|-----|-----------|---------|-------|-------|--------------------------------------|
| 1 | — | — | — | stat_total | asc | 1 | `total==151`; `items[0].stat_total==195` (minimum; **do not pin the name** — caterpie/weedle tie) |
| 2 | fire | 1 | true | id | desc | 1 | `total==1` — only moltres (146) |
| 3 | water | 1 | false | stat_total | desc | 100 | `total==32`; `items[0]` is gyarados (540) |
| 4 | water | — | false | id | asc | 100 | `total==32`; `items[0].id==7` (squirtle); `len==32` |
| 5 | fire | — | true | stat_total | asc | 100 | `total==1` — only moltres |
| 6 | — | 1 | — | id | desc | 100 | `total==151`; `items[0].id==151` (mew); `len==100` |
| 7 | water | 1 | — | id | asc | 1 | `total==32`; `items[0].id==7` (squirtle) |
| 8 | — | — | false | id | desc | 1 | `total==147`; `items[0].id==151` — mew: mythical but **not** legendary |
| 9 | fire | — | false | id | desc | 1 | `total==11` (12 fire − moltres); `items[0].id==136` (flareon) |
| 10 | fire | — | — | id | desc | 1 | `total==12`; `items[0].id==146` (moltres) |
| 11 | — | — | true | id | desc | 1 | `total==4`; `items[0].id==150` (mewtwo) |

**Shared invariants for every row:** status `200`; `len(items) <= limit`;
every active filter holds for every item; the order matches
`sort_by/sort_order`.

> Note on `limit=1` oracles: sorting is observable even on a single element —
> `items[0]` must be the extremum of the filtered set. On key ties (row 1)
> assert the **value**, not the name.

### TC-LIST-28 — LIKE wildcards in `name` · P1 · EG · 🐞 bug-candidate
The `name` value is interpolated into `ILIKE '%<name>%'` **without escaping**
LIKE special characters. Specification: the filter performs a literal
substring match.

| Request | Expected per spec | Known actual (defect) |
|---------|-------------------|------------------------|
| `?name=%` | `total==0` (no names contain a literal `%`) | `total==151` — `%` acts as a wildcard |
| `?name=_` | `total==0` (no names contain a literal `_`) | `total==151` — `_` = "any single character" |

**Automation policy:** the test encodes the **specified** expectation and is
marked `xfail` referencing the bug report until the fix (escaping `%`/`_`/`\`
before interpolating into ILIKE). See
[BUG-001](../bugs/BUG-001-like-wildcard-injection.md).

### TC-LIST-29 — Pagination with a non-unique sort key · P2 · ST/EG · 🐞 bug-candidate
The implementation sorts with `ORDER BY <key>` and **no secondary
tiebreaker**. With a non-unique key (`stat_total` has many ties) the order
inside a tie group is formally undefined → items may duplicate or vanish
across pages. (TC-LIST-26 cannot catch this: it uses the unique `id`.)

**Steps:** with `sort_by=stat_total&sort_order=desc` collect three pages
(`limit=50`, `offset=0/50/100`) and union the `id`s.
**Expected (per spec):** pages are pairwise disjoint; `|union| == 150`.
**Note:** on SQLite the order is stable in practice, so the test may pass
locally — but the API contract does not forbid unstable pagination, which is
a specification defect. Recommended API fix: `ORDER BY <key>, id`. See
[BUG-002](../bugs/BUG-002-unstable-pagination-order.md).

### TC-LIST-30 — Empty and whitespace-padded `types` · P2 · EG
The router parses CSV with trimming:
`[t.strip() for t in types.split(",") if t.strip()]`.

| Request | Expected |
|---------|----------|
| `?types=` (empty string) | `200`; the filter is not applied → `total==151` |
| `?types=,,` (separators only) | `200`; the trimmed list is empty → the filter is not applied → `total==151` |
| `?types=%20grass%20,%20poison%20` (` grass , poison `) | `200`; whitespace is trimmed → the response is **equivalent** to `?types=grass,poison` (same `total`, same `id`s); bulbasaur present |
