# Analytics — `GET /api/analytics/*`

Four aggregate endpoints. No body.

> **🔒 Access: premium.** Every route here requires the **premium** tier.
> Anonymous → `401`, free tier → `403`, premium/admin → `200`. The access
> control itself is specified in [12-rbac.md](12-rbac.md); the cases below
> assume an authenticated **premium** caller and focus on the analytics
> behavior. (Automation sends a premium bearer token via a fixture.)

- `GET /api/analytics/categories?group_by=...` — grouping by a dimension.
  `group_by` is an **enum** `[type, color, generation, habitat, shape,
  growth_rate]`, default `type`. Outside the enum → **422**.
- `GET /api/analytics/type-distribution` — distribution by type.
- `GET /api/analytics/stat-ranges` — min/max/avg per stat (for filter sliders).
- `GET /api/analytics/generation-stats` — per-generation statistics.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-ANL-01 | categories default (type) | P0 | EP |
| TC-ANL-02 | categories for every valid group_by | P1 | EP |
| TC-ANL-03 | categories invalid group_by → 422 | P1 | EP/EG |
| TC-ANL-04 | categories row invariants | P1 | EP |
| TC-ANL-05 | type-distribution structure and percentages | P1 | EP |
| TC-ANL-06 | stat-ranges structure and min≤avg≤max | P1 | EP/BVA |
| TC-ANL-07 | generation-stats for Gen I | P1 | EP |

---

### TC-ANL-01 — categories default · P0 · EP
**Request:** `GET /api/analytics/categories`
**Expected:** `200`; non-empty list; grouped as with `group_by=type` (each
`category` is a type name).

### TC-ANL-02 — Every valid `group_by` · P1 · EP
The "valid dimension" equivalence class — one representative per value.

| `group_by` | Expected |
|------------|----------|
| type | `200`, non-empty list |
| color | `200`, non-empty |
| generation | `200`, non-empty (at least one group — "1") |
| habitat | `200` (list; null habitats are excluded by the filter) |
| shape | `200` |
| growth_rate | `200` |

### TC-ANL-03 — Invalid `group_by` → 422 · P1 · EP/EG
| `group_by` | Expected |
|------------|----------|
| `weight` | `422` (outside the enum) |
| `id` | `422` |
| `''` (empty) | `422` |
| `TYPE` (case) | `422` |

### TC-ANL-04 — categories row invariants · P1 · EP
**Request:** `GET /api/analytics/categories?group_by=type`
**Expected:** for every row:
- `count >= 1`;
- `min_stat_total <= avg_stat_total <= max_stat_total`;
- all `avg_*` are numbers (rounded to 1 decimal);
- `category` is a non-empty string.

### TC-ANL-05 — type-distribution structure and percentages · P1 · EP
**Request:** `GET /api/analytics/type-distribution`
**Expected:** `200`; each element = `{type_name, count, percentage,
avg_stat_total}`;
- `count >= 1`, `0 < percentage <= 100` (per type);
- `percentage == round(count / 151 * 100, 1)`;
- sorted by `count` descending.
- *Note:* the sum of `count` across types is **greater** than 151 (dual-type
  pokemon are counted twice) — expected, not a bug.

### TC-ANL-06 — stat-ranges structure · P1 · EP/BVA
**Request:** `GET /api/analytics/stat-ranges`
**Expected:** `200`; keys `hp, attack, defense, sp_attack, sp_defense, speed,
stat_total` present; each holds `{min, max, avg}` with `min <= avg <= max`.
Known anchors: `stat_total.max == 680` (mewtwo), `stat_total.min == 195`
(caterpie/weedle), `hp.max == 250` (chansey — consistent with the TC-LIST-16e
boundary).

### TC-ANL-07 — generation-stats for Gen I · P1 · EP
**Request:** `GET /api/analytics/generation-stats`
**Expected:** `200`; a list of length 1 (only Gen I seeded);
- element: `generation==1`, `total_pokemon==151`, `avg_stat_total>0`;
- `legendary_count == 4` (articuno, zapdos, moltres, mewtwo),
  `mythical_count == 1` (mew) — the data is deterministic, so the oracle is
  exact;
- `type_distribution` is non-empty; for every row `percentage ==
  round(count / 151 * 100, 1)`.
