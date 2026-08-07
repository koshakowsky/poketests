# Security — application-layer checks

Security treated as its own category, not scattered ad-hoc. This file **owns** a
small set of focused attack-style cases and **consolidates** the security
oracles already embedded elsewhere in the catalog.

## Scope & boundary

These are **application-layer** checks against the running API. Explicitly **out
of scope** here (different layer / not owned by the app):

- **Transport encryption (TLS/HTTPS).** The dev/CI stack serves plain `http`
  behind nginx on localhost; TLS is terminated by the proxy/LB in production —
  an ops/infra concern, not testable (or meaningful) against this stack.
- **Rate limiting / brute-force throttling.** Not implemented in the SUT;
  noted here as a known absence rather than asserted.
- **Security response headers** (HSTS, CSP, X-Content-Type-Options) — nginx/proxy
  configuration, not the application.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-SEC-01 | Mass assignment — no privilege escalation at register | P0 | EG/DT |
| TC-SEC-02 | JWT `alg:none` (unsigned) token rejected | P1 | EG |
| TC-SEC-03 | Expired JWT rejected | P1 | EG/ST |
| TC-SEC-04 | SQL injection in login is neutralized | P1 | EG |
| TC-SEC-05 | Injection payload in register is stored inertly | P2 | EG |
| TC-SEC-06 | Errors don't leak internals (no stack trace / secrets) | P2 | EG |

## Consolidated — security oracles owned elsewhere

| Concern | Case(s) | File |
|---------|---------|------|
| Password / hash never in a response | TC-AUTH-15 | [10-auth.md](10-auth.md) |
| PAN / CVC never stored or returned in full | TC-BILL-17 | [11-billing-checkout.md](11-billing-checkout.md) |
| No user enumeration (identical 401) | TC-AUTH-08 | [10-auth.md](10-auth.md) |
| Tampered / wrong-secret token → 401 | TC-AUTH-13 | [10-auth.md](10-auth.md) |
| Authorization cannot be bypassed; 401-vs-403 | TC-RBAC-02/03/06/07 | [12-rbac.md](12-rbac.md) |
| CORS: foreign origin gets no allow headers | TC-XC-02 | [09-cross-cutting.md](09-cross-cutting.md) |

---

### TC-SEC-01 — No privilege escalation at register · P0 · EG/DT
The highest-value case: an attacker tries to grant themselves a higher tier (or
set server-controlled fields) by adding them to the registration body. The
server must ignore anything outside `{email, password}` — tier is assigned by
the server, never by the client.

| Register body | Expected |
|---------------|----------|
| `{email, password, "tier": "admin"}` | `201`; created user `tier == "free"` |
| `{email, password, "tier": "premium"}` | `201`; `tier == "free"` |
| `{email, password, "id": 1}` | `201`; `id` is server-assigned, not `1` |
| `{email, password, "is_admin": true}` | `201`; `tier == "free"` |

**Verify end-to-end:** log in as the newly created user and confirm a **premium**
endpoint returns `403` (not `200`) — the injected tier had no effect
(cross-ref TC-RBAC-03).

> The current schema (`RegisterRequest`) exposes only `email`/`password`, so
> Pydantic drops extra keys. The case **proves** it rather than assuming it — a
> future refactor that binds the model to the ORM (mass-assignment foot-gun)
> would be caught here.

### TC-SEC-02 — `alg:none` token rejected · P1 · EG
A forged JWT with the header algorithm set to `none` and an **empty signature**
(the classic "unsigned token" attack). The server pins `HS256` in
`jwt.decode(..., algorithms=["HS256"])`, so an `alg:none` token must not be
accepted.
**Request:** `GET /api/auth/me` with a hand-crafted `alg:none` token whose
payload claims `sub` of a real user.
**Expected:** `401`. Trusting `alg:none` would let anyone mint tokens for any
user without the secret.

> **Automation note:** no secret needed — this token is unsigned; build it by
> base64url-encoding a `{"alg":"none","typ":"JWT"}` header + payload with an
> empty third segment.

### TC-SEC-03 — Expired token rejected · P1 · EG/ST
A token correctly signed with the real secret but whose `exp` is in the past.
**Expected:** `GET /api/auth/me` → `401` (the `exp` claim is enforced by
`jwt.decode`). Confirms sessions actually expire and an old token can't be
replayed forever.

> **Automation note:** requires the SUT's `JWT_SECRET` to forge a
> signed-but-expired token. Provided to the suite via `POKETESTS_JWT_SECRET`
> (the CI stack sets both to the same value); the case **skips** with a clear
> reason when the secret isn't supplied — mirroring the `seed_token` pattern.

### TC-SEC-04 — SQL injection in login is neutralized · P1 · EG
Credential fields must be treated as data, never concatenated into SQL.

| `email` | `password` | Expected |
|---------|-----------|----------|
| `' OR '1'='1` | `x` | `401` — **not** `200`, **not** `500` |
| `admin@example.com'--` | `x` | `401` |
| `"; DROP TABLE users;--` | `x` | `401`; subsequent requests still work (table intact) |

SQLAlchemy parametrizes queries, so this is expected to be safe — the case
**documents and guards** that (regression protection akin to BUG-001's
LIKE-wildcard finding).

### TC-SEC-05 — Injection payload stored inertly · P2 · EG
**Steps:** register with `email` containing an injection/HTML payload
(`<script>alert(1)</script>@x.io`), then `GET /api/auth/me`.
**Expected:** `201` then `200`; the value round-trips **verbatim** as a plain
string (stored as data, not executed or interpreted). Any XSS concern is the
frontend's escaping responsibility (React escapes by default); the API's job is
inert storage.

### TC-SEC-06 — Errors don't leak internals · P2 · EG
**Steps:** trigger error paths — malformed JSON, wrong types, a `500`-prone
input if any — and inspect the bodies.
**Expected:** error responses contain only the intended `detail` (string, the
Pydantic `422` list, or the billing `{error_code,message}`); **no** stack
traces, file paths, SQL fragments, secret values or `hashed_password` ever
appear. Internal detail leakage aids an attacker's reconnaissance.
