# BUG-005 - `group_by` enum is documented but not enforced (silent wrong dimension)

| Field | Value |
|-------|-------|
| **Status** | **Fixed** - `Literal` type replaces the doc-only `Query(enum=...)`; test is now a regression guard |
| **Severity** | **Major** (silent wrong data - the response looks valid but answers a different question) |
| **Priority** | P1 - one-line fix, and the defect is invisible to clients |
| **Component** | API - `GET /api/analytics/categories`, `group_by` parameter |
| **Environment** | pokeanalytics, default Gen I seed |
| **Found by** | Test design - automating [TC-ANL-03](../test-cases/api/07-analytics.md) against the documented contract |
| **Automated as** | `tests/test_07_analytics.py::test_invalid_group_by_rejected` (regression guard) |

## Summary

`group_by` is declared as `Query("type", enum=[...])`. In current FastAPI the
`enum=` argument is an **OpenAPI documentation hint only - it performs no
validation**. Any string is therefore accepted, and the service silently falls
back to grouping by `color`:

```python
if category_field not in GROUPABLE_COLUMNS:
    category_field = "color"
```

So a client that asks for `group_by=habitatt` (typo) receives `200 OK` with a
well-formed body that is grouped by **color** - a different question than the
one asked, with nothing in the response indicating the substitution.

This is worse than an error: an error is visible, silent wrong data is not. It
is also a **contract violation** - `/api/openapi.json` advertises `group_by` as
an enum, so a generated client would reasonably trust that constraint.

> Contrast with `sort_by` (TC-LIST-21), where a silent fallback to `id` *is* the
> intended, documented behavior. The difference is the published schema: there
> the parameter is a free string, here it is declared an enum.

## Steps to reproduce

```bash
curl -s '.../api/analytics/categories?group_by=type'   -H "$AUTH" | jq -r '.[0].category'  # poison  (a type)
curl -s '.../api/analytics/categories?group_by=weight' -H "$AUTH" | jq -r '.[0].category'  # brown   (a COLOR)
curl -s '.../api/analytics/categories?group_by=TYPE'   -H "$AUTH" | jq -r '.[0].category'  # brown   (a COLOR)
```

## Expected result

`422 Unprocessable Entity` for any value outside
`{type, color, generation, habitat, shape, growth_rate}` - the constraint the
OpenAPI schema already advertises.

## Actual result

`200 OK` with data grouped by `color` for every out-of-enum value, including a
mere case mismatch (`TYPE`).

## Root cause

[`api/routers/analytics.py`](../../pokeanalytics/api/routers/analytics.py):

```python
group_by: str = Query("type", enum=[...])   # `enum=` documents, never validates
```

The parameter's Python type is a bare `str`, so Pydantic has no constraint to
enforce; the enum list reaches the OpenAPI schema only.

## Fix (applied)

Express the constraint in the **type**, which both validates and documents:

```python
GroupBy = Literal["type", "color", "generation", "habitat", "shape", "growth_rate"]

def categories(group_by: GroupBy = "type", ...):
```

FastAPI now rejects out-of-enum values with its standard `422`, and the OpenAPI
schema keeps the same enum. The service-level `= "color"` fallback stays as
defence in depth but is no longer reachable through the API.

## Verification (done)

`test_invalid_group_by_rejected` covers `weight`, `id`, `""` and `TYPE` → all
`422`; `test_every_valid_group_by` confirms all six valid dimensions still
return `200` with non-empty groups.
