# BUG-006 - stored type `slot` is ignored, dual-type order is wrong

| Field | Value |
|-------|-------|
| **Status** | **Fixed** - relationship now orders by `slot`; test is a regression guard |
| **Severity** | Minor (presentation/domain correctness; affects every dual-type pokemon) |
| **Priority** | P2 - one-line fix, visible in both API and UI |
| **Component** | API - `types` relation on `GET /api/pokemon/{id}` and `GET /api/pokemon/` |
| **Environment** | pokeanalytics, default Gen I seed |
| **Found by** | Test design (domain knowledge), automating [TC-DET-03](../test-cases/api/04-pokemon-detail.md) |
| **Automated as** | `tests/test_04_pokemon_detail.py::test_detail_relations_present` (regression guard) |

## Summary

The `pokemon_types` association table stores a `slot` column - the Pokémon
notion of a **primary** (slot 1) and **secondary** (slot 2) type. The
`Pokemon.types` relationship declares no `order_by`, so the ORM returns the
rows in whatever order the database yields. In practice every dual-type pokemon
comes back with its types **reversed**.

The data needed to be correct is already stored; it is simply not used.

## Steps to reproduce

```bash
curl -s .../api/pokemon/1   | jq -c '[.types[].name]'   # bulbasaur
curl -s .../api/pokemon/6   | jq -c '[.types[].name]'   # charizard
curl -s .../api/pokemon/130 | jq -c '[.types[].name]'   # gyarados
```

## Expected result

Types ordered by `slot` - the primary type first:

| Pokemon | Expected |
|---------|----------|
| bulbasaur | `["grass", "poison"]` |
| charizard | `["fire", "flying"]` |
| gyarados | `["water", "flying"]` |

## Actual result

| Pokemon | Actual |
|---------|--------|
| bulbasaur | `["poison", "grass"]` |
| charizard | `["flying", "fire"]` |
| gyarados | `["flying", "water"]` |

Every dual-type pokemon is affected - roughly half the roster - and the wrong
order propagates to the UI type badges.

## Root cause

[`api/models.py`](../../pokeanalytics/api/models.py):

```python
types = relationship("Type", secondary=pokemon_types, back_populates="pokemon")
```

No `order_by`, so the `slot` column in the association table is written at seed
time and never read back.

## Fix (applied)

```python
types = relationship(
    "Type",
    secondary=pokemon_types,
    back_populates="pokemon",
    order_by=pokemon_types.c.slot,
)
```

## Verification (done)

`test_detail_relations_present` asserts charizard is exactly
`["fire", "flying"]` (order-sensitive). Single-type pokemon are unaffected, and
the list endpoint shares the same relationship, so it is fixed in both places.

> Why an order-sensitive assertion instead of a set comparison: the slot is
> domain-meaningful (primary vs secondary type). Relaxing the oracle to a set
> would have made the test pass and hidden the defect.
