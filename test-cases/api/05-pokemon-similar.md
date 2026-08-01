# Pokemon Similar — `GET /api/pokemon/{pokemon_id}/similar`

Returns a list of similar pokemon (`SimilarPokemon[]`) sorted by
`similarity_score` descending. Metric: 50% stats (cosine + magnitude), 30%
type overlap, 20% meta (generation/habitat/color/legendary flag).
`limit` parameter — `Query(10, ge=1, le=50)`. Unknown pokemon → 404.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-SIM-01 | Similar for an existing pokemon | P0 | EP |
| TC-SIM-02 | Sorted by score descending | P1 | EP |
| TC-SIM-03 | The pokemon itself is not in the result | P1 | EG |
| TC-SIM-04 | `limit` boundaries | P1 | BVA |
| TC-SIM-05 | Unknown pokemon → 404 | P0 | EP |
| TC-SIM-06 | Score and matching_types invariants | P2 | EP |
| TC-SIM-07 | Domain plausibility | P2 | EG |

---

### TC-SIM-01 — Similar for an existing pokemon · P0 · EP
**Request:** `GET /api/pokemon/1/similar`
**Expected:** `200`; a list of 10 entries (default limit); each has
`pokemon`, `similarity_score`, `matching_types`, `stat_difference`.

### TC-SIM-02 — Sorted by score descending · P1 · EP
**Request:** `GET /api/pokemon/1/similar?limit=20`
**Expected:** `200`; `similarity_score` is non-increasing over the list.

### TC-SIM-03 — Self is excluded · P1 · EG
**Request:** `GET /api/pokemon/25/similar?limit=50`
**Expected:** no entry has `pokemon.id == 25`.

### TC-SIM-04 — `limit` boundaries · P1 · BVA
Rule: `ge=1, le=50`.

| `limit` | Expected |
|---------|----------|
| 0 | `422` |
| 1 | `200`, `len==1` |
| 50 | `200`, `len==50` |
| 51 | `422` |
| -1 | `422` |

### TC-SIM-05 — Unknown pokemon → 404 · P0 · EP
**Request:** `GET /api/pokemon/999999/similar`
**Expected:** `404`; `body.detail == "Pokemon not found"`.

### TC-SIM-06 — Field invariants · P2 · EP
**Request:** `GET /api/pokemon/1/similar`
**Expected:**
- `0 <= similarity_score <= 100` for all entries;
- `stat_difference >= 0`;
- `matching_types` ⊆ the target pokemon's types (for id=1 — a subset of
  `{grass, poison}`).

### TC-SIM-07 — Domain plausibility · P2 · EG
**Request:** `GET /api/pokemon/1/similar` (bulbasaur)
**Expected:** its evolutions / profile neighbours are expectedly near the top
(ivysaur id=2, venusaur id=3) with a higher score than unrelated pokemon.
Soft check: ivysaur is in the top 5.
