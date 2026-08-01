# BUG-001 — `name` filter: LIKE wildcards are not escaped (pattern injection)

| Field | Value |
|-------|-------|
| **Status** | **Fixed** — escaping applied in `pokemon_service.py`; `xfail` removed, test is now a regression guard |
| **Severity** | Minor (correctness; no data exposure in this SUT) |
| **Priority** | P1 — trivial fix, spec-encoding tests already exist |
| **Component** | API — `GET /api/pokemon/` (list/search), `name` filter |
| **Environment** | pokeanalytics `dev`, default Gen I seed (151 pokemon); reproducible on SQLite and PostgreSQL |
| **Found by** | Test design (error guessing), case [TC-LIST-28](../test-cases/03-pokemon-list-search.md#tc-list-28--like-wildcards-in-name--p1--eg---bug-candidate) |
| **Automated as** | `tests/test_03_pokemon_list.py::test_name_filter_treats_like_wildcards_literally` (regression guard) |

## Summary

The `name` query parameter is interpolated into an `ILIKE '%<name>%'` pattern
without escaping the LIKE special characters `%`, `_` and `\`. User input can
therefore change the *matching semantics* of the filter instead of being
searched literally.

Note: this is **not** SQL injection — the value is passed as a bound
parameter and cannot escape the string context. It is LIKE *pattern*
injection: a narrower but real correctness defect. In systems where a similar
filter scopes access-controlled rows, the same defect class broadens the
result set — which is why the fix pattern matters beyond this SUT.

## Steps to reproduce

```bash
curl -s 'http://localhost/api/pokemon/?name=%25' | jq .total   # name=%
curl -s 'http://localhost/api/pokemon/?name=_'   | jq .total
```

## Expected result

No Gen I pokemon name contains a literal `%` or `_`, so both requests must
return `total == 0` (the filter performs a literal substring match).

## Actual result

Both requests return `total == 151`: `%` matches any string and `_` matches
any single character, so the pattern `%_%` / `%%%` matches every name.

## Root cause

[`api/services/pokemon_service.py`](../../pokeanalytics/api/services/pokemon_service.py):

```python
query = query.filter(Pokemon.name.ilike(f"%{params.name}%"))
```

The raw value went into the pattern; LIKE metacharacters kept their special
meaning.

## Fix (applied)

Escape the three metacharacters and declare the escape character:

```python
escaped = (
    params.name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
)
query = query.filter(Pokemon.name.ilike(f"%{escaped}%", escape="\\"))
```

`escape=` is supported by SQLAlchemy on both SQLite and PostgreSQL.

## Verification (done)

`xfail` removed from `test_name_filter_treats_like_wildcards_literally`; it now
passes and stands as the permanent regression guard. TC-LIST-03/04/05 confirm
normal substring search is unaffected.
