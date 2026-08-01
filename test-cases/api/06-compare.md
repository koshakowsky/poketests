# Compare — `POST /api/compare/`

Body: `{"pokemon_ids": [int, ...]}`. Compares 2–6 pokemon.

**Rules (two-level validation):**
1. **The router** validates the raw array length: `< 2` → 400 "At least 2
   Pokemon are required"; `> 6` → 400 "The maximum is 6 Pokemon".
2. **The service** de-duplicates the ids and drops unknown ones; if fewer
   than 2 unique existing remain → 400 "Need at least 2 pokemon to compare".
   The result order matches the request order.

**Response:** `{ pokemon[], stat_comparison{}, advantages{} }`:
- `stat_comparison[stat]` for `hp, attack, defense, sp_attack, sp_defense,
  speed, stat_total`: `{ values{name:val}, max, min, leader[], spread }`;
- `advantages[name][other]` = `{ type_advantage{best_multiplier, details,
  verdict}, stat_advantage{stats_won, stats_lost, stats_tied, details} }`.

---

## Decision table (DT) — admission to comparison

| Raw id count | Unique existing | Expected |
|--------------|-----------------|----------|
| < 2 | — | 400 (router: "At least 2…") |
| 2..6 | ≥ 2 | 200 |
| 2..6 | < 2 (dupes/unknown) | 400 (service: "Need at least 2…") |
| > 6 | — | 400 (router: "maximum is 6") |

---

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-CMP-01 | Compare two pokemon (happy) | P0 | EP |
| TC-CMP-02 | Id count — boundaries 2..6 | P0 | BVA |
| TC-CMP-03 | Duplicates collapse | P1 | EG/DT |
| TC-CMP-04 | Unknown ids are filtered out | P1 | EG/DT |
| TC-CMP-05 | All ids unknown → 400 | P1 | DT |
| TC-CMP-06 | Invalid body → 422 | P1 | EG |
| TC-CMP-07 | stat_comparison structure and leader | P1 | EP |
| TC-CMP-08 | advantages structure | P2 | EP |
| TC-CMP-09 | Result order = request order | P2 | EP |

---

### TC-CMP-01 — Compare two (happy) · P0 · EP
**Request:** `POST /api/compare/` body `{"pokemon_ids": [1, 4]}`
**Expected:** `200`; `len(pokemon)==2`; keys `stat_comparison` and
`advantages` present; names `bulbasaur`, `charmander`.

### TC-CMP-02 — Id count boundaries · P0 · BVA
| `pokemon_ids` | Class | Expected |
|---------------|-------|----------|
| `[]` | 0, empty | 400 ("At least 2…") |
| `[1]` | 1, below bound | 400 ("At least 2…") |
| `[1,4]` | 2, lower bound | 200 |
| `[1,2,3,4,5,6]` | 6, upper bound | 200, `len(pokemon)==6` |
| `[1,2,3,4,5,6,7]` | 7, above bound | 400 ("maximum is 6") |

### TC-CMP-03 — Duplicates collapse · P1 · EG/DT
| `pokemon_ids` | Expected |
|---------------|----------|
| `[1,1]` | 400 — 1 unique after dedup ("Need at least 2…") |
| `[1,1,4]` | 200 — dedup to `[1,4]`, `len(pokemon)==2` |
| `[1,4,4,1]` | 200 — dedup to `[1,4]` |

### TC-CMP-04 — Unknown ids are filtered out · P1 · EG/DT
Unknown ids (including negatives — the type is valid, the row is absent) are
dropped by the service; the "at least 2" rule applies to what remains.

| `pokemon_ids` | Expected |
|---------------|----------|
| `[1, 4, 999999]` | `200`; `len(pokemon)==2` (1 and 4 remain); 999999 absent |
| `[1, -1]` | `400` — one existing pokemon left after filtering ("Need at least 2…") |
| `[1, 4, -1]` | `200`; `len(pokemon)==2` |

### TC-CMP-05 — All ids unknown → 400 · P1 · DT
**Request:** `{"pokemon_ids": [999998, 999999]}`
**Expected:** `400`; `body.detail == "Need at least 2 pokemon to compare"`.

### TC-CMP-06 — Invalid body → 422 · P1 · EG
| Body | Expected |
|------|----------|
| `{}` (field missing) | 422 |
| `{"pokemon_ids": "1,2"}` (string, not array) | 422 |
| `{"pokemon_ids": [1, "a"]}` (non-number in array) | 422 |
| `{"pokemon_ids": [1.5, 2.5]}` (floats) | 422 |
| (empty body / not JSON) | 422 |

### TC-CMP-07 — stat_comparison structure and leader · P1 · EP
**Request:** `{"pokemon_ids": [1, 150]}` (bulbasaur 318 vs mewtwo 680)
**Expected:** `200`;
- `stat_comparison` has all 7 keys (`hp…speed`, `stat_total`);
- for `stat_total`: `values["mewtwo"]==680`, `values["bulbasaur"]==318`,
  `max==680`, `min==318`, `spread==362`, `leader==["mewtwo"]`;
- invariant for every stat: `max == max(values)`, `min == min(values)`,
  `spread == max - min`, `leader` contains names with `value == max`.

### TC-CMP-08 — advantages structure · P2 · EP
**Request:** `{"pokemon_ids": [1, 4]}`
**Expected:**
- `advantages` keyed by each name; each holds entries against the others
  (but not against itself);
- `stat_advantage`: `stats_won + stats_lost + stats_tied == 6`;
- `type_advantage.verdict ∈ {super_effective, not_effective, neutral}` and is
  consistent with `best_multiplier` (>1 → super_effective, <1 →
  not_effective, ==1 → neutral).

### TC-CMP-09 — Result order · P2 · EP
**Request:** `{"pokemon_ids": [4, 1, 7]}`
**Expected:** `pokemon[].id == [4, 1, 7]` (request order preserved).
