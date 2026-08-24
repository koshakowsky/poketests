# BUG-004 - out-of-range integer params return 500 (SQLite overflow)

| Field | Value |
|-------|-------|
| **Status** | **Fixed** - global `OverflowError` handler → 400; contract suite is the guard |
| **Severity** | Minor→Medium (robustness/availability: unhandled 500 on a class of inputs) |
| **Priority** | P1 - one-line fix, affects every integer path/query param |
| **Component** | API - any `int` path/query param backed by a DB query (pokemon detail/similar, list/search filters, types effectiveness) |
| **Environment** | pokeanalytics, default Gen I seed; SQLite |
| **Found by** | **Contract fuzzing** (schemathesis, `not_a_server_error` check) against the live OpenAPI schema |
| **Automated as** | `contract/tests/test_contract.py::test_contract` (schemathesis; the fuzzed `not_a_server_error` check is the permanent guard) |

## Summary

Integer path/query parameters are typed `int`, which in Python is unbounded.
A value beyond SQLite's signed 64-bit range (`9223372036854775808` = 2⁶³, one
past `INT64_MAX`) reaches the query layer and the driver raises
`OverflowError: Python int too large to convert to SQLite INTEGER`. Unhandled,
it surfaces as a **500**.

FastAPI/Pydantic don't catch it because the value *is* a valid integer at the
type level - the range limit belongs to the storage engine, not the schema. So
every endpoint with a DB-bound int param shares the defect.

## Steps to reproduce

```bash
curl -s -o /dev/null -w '%{http_code}\n' 'http://localhost/api/pokemon/9223372036854775808'
curl -s -o /dev/null -w '%{http_code}\n' 'http://localhost/api/pokemon/?generation=9223372036854775808'
curl -s -o /dev/null -w '%{http_code}\n' 'http://localhost/api/types/9223372036854775808/effectiveness'
```

## Expected result

A bad request (`400`) - the value is out of the acceptable range - not a `500`.
A server error implies the fault is ours; a range-exceeding input is the
client's.

## Actual result

All three return `500`; the log shows
`OverflowError: Python int too large to convert to SQLite INTEGER`.

## Root cause

`int` path/query params have no upper bound, and the overflow raised when
binding the value to the SQLite query was never handled. It is a whole *class*
of inputs across many endpoints, not a single route - so the fix is centralized
rather than per-parameter.

## Fix (applied)

A single application-level exception handler ([`api/main.py`](../../pokeanalytics/api/main.py)):

```python
@app.exception_handler(OverflowError)
async def integer_out_of_range(request: Request, exc: OverflowError):
    return JSONResponse(status_code=400, content={"detail": "Integer value out of range"})
```

`OverflowError` is specific to this overflow, so the handler doesn't mask
unrelated server errors. All valid (representable) integers keep their existing
behavior; only the out-of-range ones now get a clean `400`.

## Verification (done)

Re-running the contract suite (schemathesis, `not_a_server_error`) no longer
finds a 500 on any operation. Because the check fuzzes schema-derived inputs, it
stands as an ongoing guard against this and similar robustness regressions.
