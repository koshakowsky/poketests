# Types — `GET /api/types/` and `GET /api/types/{type_id}/effectiveness`

- `GET /api/types/` — all types (`TypeSchema[]`), sorted by name.
- `GET /api/types/{type_id}/effectiveness` — effectiveness table:
  `{ attacking[], defending[] }`, each element = `{type, multiplier}`.
  Only non-neutral multipliers are stored: `2.0` (super effective), `0.5`
  (not very effective), `0.0` (immune). Unknown `type_id` → **404**.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-TYP-01 | Type list | P0 | EP |
| TC-TYP-02 | List sorted by name | P2 | EP |
| TC-TYP-03 | Effectiveness of an existing type | P0 | EP |
| TC-TYP-04 | Unknown type_id → 404 | P0 | EP |
| TC-TYP-05 | Malformed type_id → 422 | P2 | EG |
| TC-TYP-06 | Domain correctness of multipliers | P1 | EP |

---

### TC-TYP-01 — Type list · P0 · EP
**Request:** `GET /api/types/`
**Expected:** `200`; non-empty list; each element = `{id, name}`; known
names present (`fire`, `water`, `grass`, `electric`).

### TC-TYP-02 — Sorted by name · P2 · EP
**Request:** `GET /api/types/`
**Expected:** names are in ascending alphabetical order.

### TC-TYP-03 — Effectiveness of an existing type · P0 · EP
**Precondition:** take the `fire` type id from `GET /api/types/`.
**Request:** `GET /api/types/{fire_id}/effectiveness`
**Expected:** `200`; keys `attacking` and `defending` (lists); each element =
`{type, multiplier}` with a numeric `multiplier`.

### TC-TYP-04 — Unknown type_id → 404 · P0 · EP
**Request:** `GET /api/types/999999/effectiveness`
**Expected:** `404`; `body.detail == "Type not found"`.

### TC-TYP-05 — Malformed type_id → 422 · P2 · EG
| `type_id` | Expected |
|-----------|----------|
| `abc` | `422` (does not coerce to int) |
| `1.5` | `422` |

### TC-TYP-06 — Domain correctness of multipliers · P1 · EP
**Request:** `GET /api/types/{fire_id}/effectiveness`
**Expected (Pokémon domain):**
- `attacking` for fire contains `grass` with `multiplier == 2.0` (fire is
  strong against grass);
- `attacking` for fire contains `water` with `multiplier == 0.5` (fire is
  weak against water);
- all `multiplier ∈ {0.0, 0.5, 2.0}` (neutral 1.0 is not stored).
