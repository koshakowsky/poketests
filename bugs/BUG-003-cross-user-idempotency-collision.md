# BUG-003 — checkout idempotency key collides across users (500)

| Field | Value |
|-------|-------|
| **Status** | **Fixed** — idempotency scoped per user (composite PK `(user_id, key)`); guard test added |
| **Severity** | Minor (robustness/availability; unhandled `IntegrityError` → 500, cross-tenant coupling) |
| **Priority** | P2 — low likelihood (client-generated keys), but a 500 and a tenant-isolation smell |
| **Component** | API — `POST /api/billing/checkout`, idempotency handling |
| **Environment** | pokeanalytics auth build, default Gen I seed; SQLite |
| **Found by** | Test design (state/idempotency), while automating [TC-BILL-11](../test-cases/api/11-billing-checkout.md); guarded by [TC-BILL-19](../test-cases/api/11-billing-checkout.md#tc-bill-19--idempotency-key-is-scoped-per-user--p2--st--bug-003) |
| **Automated as** | `tests/test_11_billing.py::test_idempotency_key_is_scoped_per_user` (regression guard) |

## Summary

The `idempotency_key` on checkout is stored with the **key alone** as the
primary key, so keys share one global namespace across all users. But the
cache-hit lookup is **user-scoped** (`cached.user_id == user.id`). When two
different users present the same key, the lookup misses (different user), the
request proceeds to the charge, and the final `INSERT` violates the primary-key
uniqueness — surfacing as an unhandled `500`.

Idempotency keys are client-generated, so a real collision is unlikely, but the
design couples unrelated tenants: one user's key can make another user's request
fail. Payment gateways scope idempotency keys per account for exactly this
reason.

## Steps to reproduce

Two different users send a checkout with the **same** `idempotency_key`:

```bash
# user A
curl -s -X POST .../api/billing/checkout -H "Authorization: Bearer $TOKEN_A" \
  -d '{"plan_id":"premium","card":{...},"idempotency_key":"shared"}'   # 200

# user B, same key
curl -s -o /dev/null -w '%{http_code}' -X POST .../api/billing/checkout \
  -H "Authorization: Bearer $TOKEN_B" \
  -d '{"plan_id":"premium","card":{...},"idempotency_key":"shared"}'   # 500
```

## Expected result

The key is scoped to the caller: user B's request succeeds independently
(`200`, B's own subscription). One user must never be able to affect another
user's request through a shared key.

## Actual result

User B receives `500`; the server log shows
`sqlite3.IntegrityError: UNIQUE constraint failed: idempotency_keys.key`.

## Root cause

[`api/models.py`](../../pokeanalytics/api/models.py) — the key alone is the
primary key:

```python
class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    key = Column(String(255), primary_key=True)      # global namespace
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
```

while [`api/routers/billing.py`](../../pokeanalytics/api/routers/billing.py)
reads it back per user, so a foreign key is never a cache hit and always falls
through to the colliding `INSERT`.

## Fix (applied)

Scope idempotency to the user by making the primary key composite
`(user_id, key)`, and look it up by both:

```python
# models.py
user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
key = Column(String(255), primary_key=True)

# billing.py
cached = db.get(IdempotencyKey, {"user_id": user.id, "key": body.idempotency_key})
if cached is not None:
    response.status_code = cached.status_code
    return json.loads(cached.response_json)
```

The same-user replay behavior is unchanged; the per-user guard on the cache read
is now inherent in the lookup. (No migration script: the SUT builds schema via
`create_all` on hermetic, recreated databases.)

## Verification (done)

`test_idempotency_key_is_scoped_per_user` (TC-BILL-19): two users reuse one key,
both get `200`, both end up premium. TC-BILL-11 confirms same-user replay still
returns the identical body.
