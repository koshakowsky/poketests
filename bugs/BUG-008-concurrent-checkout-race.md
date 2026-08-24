# BUG-008 - concurrent double-submit of checkout returns 500 (TOCTOU race)

| Field | Value |
|-------|-------|
| **Status** | **Fixed** - the unique-constraint collision is handled and resolved to the winner's state |
| **Severity** | **Major** (a successful payment is reported to the user as a server error) |
| **Priority** | P1 - double-clicking Pay is ordinary user behaviour, not an edge case |
| **Component** | API - `POST /api/billing/checkout` |
| **Environment** | pokeanalytics auth build, default Gen I seed; SQLite |
| **Found by** | Test design (concurrency), case [TC-BILL-20](../test-cases/api/11-billing-checkout.md) |
| **Automated as** | `tests/test_11_billing.py::test_concurrent_double_submit_charges_once` (regression guard) |

## Summary

Checkout is **check-then-act**: it looks up the idempotency cache, then checks
for an active subscription, then charges and inserts. All three steps happen
outside any lock, so two requests that arrive at the same time both find "no
subscription yet" and both proceed to insert. The unique index on
`subscriptions.user_id` correctly rejects the second - but nothing catches the
`IntegrityError`, so it escaped as a **500**.

The user experience is the worst possible combination: the payment succeeded and
the subscription exists, yet the browser shows a server error. The user
reasonably assumes it failed and tries again.

Note this is a **different race** from [BUG-003](BUG-003-cross-user-idempotency-collision.md).
That one was two *different users* sharing a key (a schema problem, fixed with a
composite primary key). This one is the *same user* submitting twice
concurrently - a sequencing problem that no schema change prevents, and which
the sequential idempotency test (TC-BILL-11) structurally cannot observe: the
replay only works once the first request has already committed its cache entry.

## Steps to reproduce

Fire two identical checkouts in parallel for one user with one
`idempotency_key`:

```python
with ThreadPoolExecutor(max_workers=2) as pool:
    responses = [f.result() for f in [pool.submit(checkout, key="k") for _ in range(2)]]
print(sorted(r.status_code for r in responses))   # [200, 500]
```

Reproduced on 3/3 attempts before the fix.

## Expected result

Exactly one subscription, no server error. Either both requests return `200`
with the same body (the cache absorbed the duplicate) or one returns `200` and
the other `409 already_subscribed` (the state guard absorbed it).

## Actual result

`[200, 500]`; the log shows
`sqlalchemy.exc.IntegrityError: UNIQUE constraint failed: subscriptions.user_id`.

## Root cause

[`api/routers/billing.py`](../../pokeanalytics/api/routers/billing.py): the read
that decides whether to insert and the insert itself are not atomic:

```python
existing = db.query(Subscription).filter(...).first()   # both see None
if existing is not None and existing.status == "active":
    raise HTTPException(409, ...)
...
db.add(Subscription(user_id=user.id))
db.commit()                                             # second one explodes
```

## Fix (applied)

Rather than widening the lock, let the database constraint be the arbiter (it
already is) and handle the loss of the race:

```python
try:
    db.commit()
except IntegrityError:
    db.rollback()
    winner = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if winner is None:
        raise
    return _sub_out(winner)
```

The same guard wraps the idempotency-key insert, where the identical race is
harmless (the concurrent request has already cached the response).

The DB constraint remains the single source of mutual exclusion, so the fix
holds regardless of how many workers or processes serve the request - unlike an
application-level lock, which would not survive the multi-worker gunicorn
deployment.

> **Known limitation, deliberately not addressed here.** The *charge* still
> happens twice against the fake gateway before the constraint arbitrates.
> A fully correct design claims the idempotency key **before** charging, so the
> key acts as the lock, and releases it if the charge fails. That is a larger
> refactor with its own failure modes (a crashed request leaving a claimed key),
> and against a real PSP the gateway's own idempotency would dedupe the charge
> anyway. The observable API contract - one subscription, no 500 - is what this
> fix guarantees, and TC-BILL-20 pins it.

## Verification (done)

`test_concurrent_double_submit_charges_once` passes 5/5 consecutive runs; the
oracle asserts the invariant (exactly one active subscription, tier premium, no
500) rather than a specific status pair, since both `[200, 200]` and
`[200, 409]` are correct single-charge outcomes.
