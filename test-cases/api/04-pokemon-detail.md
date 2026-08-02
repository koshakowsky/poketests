# Pokemon Detail — `GET /api/pokemon/{pokemon_id}`

Returns the full card (`PokemonDetail`) with the computed fields `height_m`,
`weight_kg` and the `types`, `abilities`, `egg_groups` relations.
`pokemon_id` is an int path parameter. Unknown id → 404.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-DET-01 | Detail of an existing pokemon | P0 | EP |
| TC-DET-02 | Computed fields height_m/weight_kg | P1 | EP |
| TC-DET-03 | types/abilities/egg_groups relations present | P1 | EP |
| TC-DET-04 | Unknown id → 404 | P0 | EP |
| TC-DET-05 | Boundary/malformed ids | P1 | BVA/EG |

---

### TC-DET-01 — Detail of an existing pokemon · P0 · EP
**Request:** `GET /api/pokemon/1`
**Expected:** `200`; `id==1`, `name=="bulbasaur"`, `stat_total==318`;
`types` contains `grass` and `poison`.

### TC-DET-02 — Computed fields · P1 · EP
**Request:** `GET /api/pokemon/1`
**Expected:** `height_m` and `weight_kg` are present as floats, consistent
with the raw `height`/`weight` (`height_m == round(height/10, 1)`).

### TC-DET-03 — Relations present · P1 · EP
**Request:** `GET /api/pokemon/6` (charizard)
**Expected:** `200`; `types` = `[fire, flying]` (by slot); `abilities` is a
non-empty list with a `name` field; `egg_groups` is a list.

### TC-DET-04 — Unknown id → 404 · P0 · EP
**Request:** `GET /api/pokemon/999999`
**Expected:** `404`; `body.detail == "Pokemon not found"`.

### TC-DET-05 — Boundary/malformed ids · P1 · BVA/EG
| `pokemon_id` | Class | Expected |
|--------------|-------|----------|
| 1 | lowest valid (exists in DB) | `200` |
| 151 | upper bound of the seeded set | `200` (mew) |
| 152 | just past the set | `404` |
| 0 | type-valid, no such id | `404` |
| -1 | negative | `404` *(a valid int, no such row)* |
| abc | non-numeric | `422` (path does not coerce to int) |
| 1.5 | float | `422` |

> The 404/422 distinction matters: `-1` is a valid int that simply does not
> exist (404), while `abc` fails type parsing (422). Merging these classes
> into one "negative" case would hide validation regressions.
