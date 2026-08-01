# BUG-002 — Pagination order is undefined for non-unique sort keys (no tiebreaker)

| Field | Value |
|-------|-------|
| **Status** | **Fixed** — `ORDER BY <key>, id` tiebreaker added in `pokemon_service.py` |
| **Severity** | Major on PostgreSQL (user-visible duplicates/losses while paging), latent on SQLite |
| **Priority** | P1 — one-line fix; defect is environment-dependent and intermittent by nature |
| **Component** | API — `GET /api/pokemon/` (list/search), sorting + pagination |
| **Environment** | pokeanalytics `dev`; masked on SQLite, expected to manifest on PostgreSQL (`DATABASE_URL` explicitly supports it) |
| **Found by** | Test design (state/sequencing analysis), case [TC-LIST-29](../test-cases/03-pokemon-list-search.md#tc-list-29--pagination-with-a-non-unique-sort-key--p2--steg---bug-candidate) |
| **Automated as** | `tests/test_03_pokemon_list.py::test_pagination_stable_with_non_unique_sort_key` (regression guard) |

## Summary

The list endpoint sorts with `ORDER BY <sort_column>` only. SQL does not
define the relative order of rows with equal sort-key values, and pagination
issues a **separate query per page**. If the database orders a tie group
differently between those queries, an item can appear on two pages while
another item appears on none.

`stat_total` (the **default** sort key) has many ties in the dataset, so the
default listing is exactly the affected path.

## Steps to reproduce

Deterministically reproducible only where the DB reorders ties (PostgreSQL,
parallel scans); on SQLite the order is stable in practice, which is why the
defect is *latent*, not absent — the API contract simply does not promise
stable pagination:

```bash
# Collect three pages and count unique ids — must be 150:
for off in 0 50 100; do
  curl -s "http://localhost/api/pokemon/?sort_by=stat_total&sort_order=desc&limit=50&offset=$off" \
    | jq -r '.items[].id'
done | sort | uniq | wc -l
```

## Expected result

Pages are pairwise disjoint; the union of three 50-item pages over 151 rows
contains exactly 150 unique ids, on any supported database.

## Actual result

Not guaranteed by the implementation: tie order within `ORDER BY stat_total`
is unspecified, so the count can be < 150 (duplicates + losses) depending on
the database and query plan.

## Root cause

[`api/services/pokemon_service.py`](../../pokeanalytics/api/services/pokemon_service.py):

```python
query = query.order_by(order_func(sort_column))
```

No secondary key ⇒ non-deterministic total order whenever `sort_column` is
non-unique.

## Fix (applied)

Append the unique primary key as the tiebreaker:

```python
order_clauses = [order_func(sort_column)]
if sort_by != "id":
    order_clauses.append(asc(Pokemon.id))
query = query.order_by(*order_clauses)
```

## Side benefit for testability

With the tiebreaker the API becomes fully deterministic: the caterpie/weedle
tie in pairwise case TC-LIST-27 row 1 resolves by `id`, and the catalog
oracle can be tightened from "assert the value" to "assert the exact name".

## Verification plan

Run the TC-LIST-29 page-disjointness check on both SQLite and PostgreSQL;
tighten the TC-LIST-27 row 1 oracle; keep the disjointness test as a
permanent regression guard.
