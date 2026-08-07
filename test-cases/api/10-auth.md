# Auth — `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`

Registration, login and self-lookup. Authentication is **JWT bearer**: login
returns a signed token; protected routes read it from
`Authorization: Bearer <token>`. Tier-based access control (who may call what)
is specified separately in [12-rbac.md](12-rbac.md) — this file covers the auth
endpoints themselves.

**Contract:**
- `POST /api/auth/register` — body `{email, password}`. Creates a **free** user.
  `201` with `UserOut` `{id, email, tier}`. Duplicate email → `409`. Password
  has a minimum length (`min_length=8`, a Pydantic constraint) → `422` below it.
- `POST /api/auth/login` — body `{email, password}`. Valid → `200`
  `{access_token, token_type:"bearer"}`. Bad credentials → `401`.
- `GET /api/auth/me` — bearer required. Valid → `200` `UserOut`. Missing /
  malformed / tampered / expired token → `401`.

**Shared oracle (security):** no auth response ever echoes the password or its
hash. `UserOut` is exactly `{id, email, tier}`; the test-side model
(`extra="forbid"`) fails if `hashed_password` ever leaks.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-AUTH-01 | Register a new user → 201, free tier | P0 | EP |
| TC-AUTH-02 | Register duplicate email → 409 | P1 | EG/DT |
| TC-AUTH-03 | Password length boundary (min 8) | P1 | BVA |
| TC-AUTH-04 | Register invalid body → 422 | P1 | EG |
| TC-AUTH-05 | Email format is **not** validated (documents actual) | P2 | EG |
| TC-AUTH-06 | Login happy → 200 + bearer token | P0 | EP |
| TC-AUTH-07 | Login wrong password → 401 | P0 | EP |
| TC-AUTH-08 | Login unknown email → 401 (no user enumeration) | P1 | EG/security |
| TC-AUTH-09 | Login invalid body → 422 | P2 | EG |
| TC-AUTH-10 | `/me` with a valid token → 200 | P0 | ST |
| TC-AUTH-11 | `/me` without a token → 401 | P0 | EP |
| TC-AUTH-12 | `/me` with a malformed/garbage token → 401 | P1 | EG |
| TC-AUTH-13 | `/me` with a tampered / wrong-secret token → 401 | P1 | EG/security |
| TC-AUTH-14 | Round-trip register → login → me is consistent | P1 | ST |
| TC-AUTH-15 | Password / hash never returned | P1 | security |

---

### TC-AUTH-01 — Register a new user · P0 · EP
**Request:** `POST /api/auth/register` body `{"email": "<unique>", "password": "password123"}`
**Expected:** `201`; body `{id, email, tier}`; `email` echoes the input;
`tier == "free"`; `id` is a positive int. New accounts always start free —
premium is reached only through checkout ([11-billing-checkout.md](11-billing-checkout.md)).

> **Automation note:** email must be unique per run (the suite owns no reset
> between tests). Generate it — e.g. `f"user+{uuid4().hex}@test.io"` — so
> re-runs and parallel workers don't collide on the `409` path.

### TC-AUTH-02 — Duplicate email → 409 · P1 · EG/DT
**Steps:** register an email, then register the **same** email again.
**Expected:** first → `201`; second → `409`; `body.detail == "Email already
registered"`. Case-sensitivity of the email is exercised by TC-AUTH-05.

### TC-AUTH-03 — Password length boundary · P1 · BVA
Rule: `password` has `min_length=8`. Boundaries around 8.

| password length | Example | Expected |
|-----------------|---------|----------|
| 7 (below) | `"1234567"` | `422` (Pydantic validation) |
| 8 (lower bound) | `"12345678"` | `201` |
| 9 (above) | `"123456789"` | `201` |
| 0 (empty) | `""` | `422` |

> This is a Pydantic constraint, so the error is the framework's
> `422 {"detail": [...]}`, **not** a business `{"detail": "<text>"}`.

### TC-AUTH-04 — Invalid body → 422 · P1 · EG
| Body | Expected |
|------|----------|
| `{"password": "password123"}` (no email) | `422` |
| `{"email": "a@b.io"}` (no password) | `422` |
| `{}` | `422` |
| (empty / not JSON) | `422` |

### TC-AUTH-05 — Email format is not validated · P2 · EG
**Documents actual behavior, not desired.** The backend types `email` as a
plain `str` (not Pydantic `EmailStr`), so a syntactically invalid email is
**accepted**.
**Request:** `POST /api/auth/register` `{"email": "not-an-email", "password": "password123"}`
**Expected (current):** `201` — the value is stored verbatim.
> **Finding (low severity):** absence of email-format validation. Captured as a
> catalog observation; a candidate bug report if the product intends real
> emails. The case pins the *current* contract so a future switch to `EmailStr`
> (which would return `422`) is a visible, intentional change — not a silent
> surprise.

### TC-AUTH-06 — Login happy → 200 + bearer · P0 · EP
**Precondition:** a registered user (TC-AUTH-01).
**Request:** `POST /api/auth/login` `{email, password}`
**Expected:** `200`; body `{access_token, token_type}`; `token_type == "bearer"`;
`access_token` is a non-empty string with three dot-separated segments (JWT).

### TC-AUTH-07 — Wrong password → 401 · P0 · EP
**Request:** `POST /api/auth/login` with a correct email, wrong password.
**Expected:** `401`; `body.detail == "Invalid email or password"`.

### TC-AUTH-08 — Unknown email → 401, no enumeration · P1 · EG/security
**Request:** `POST /api/auth/login` with an email that was never registered.
**Expected:** `401` with the **same** `detail` as TC-AUTH-07 ("Invalid email or
password"). A different message/status for "unknown user" vs "wrong password"
would leak which emails exist (user enumeration) — the oracle asserts they are
indistinguishable.

### TC-AUTH-09 — Login invalid body → 422 · P2 · EG
Missing `email`, missing `password`, empty body → `422` (framework validation,
before any credential check).

### TC-AUTH-10 — `/me` with a valid token → 200 · P0 · ST
**Request:** `GET /api/auth/me` with `Authorization: Bearer <valid token>`
**Expected:** `200`; body `{id, email, tier}` matching the logged-in user.

### TC-AUTH-11 — `/me` without a token → 401 · P0 · EP
**Request:** `GET /api/auth/me` with **no** `Authorization` header.
**Expected:** `401`; `body.detail == "Not authenticated"`; response carries
`WWW-Authenticate: Bearer`. (Missing credentials → 401, never 403 — see
[12-rbac.md](12-rbac.md) for the 401-vs-403 rule.)

### TC-AUTH-12 — Malformed / garbage token → 401 · P1 · EG
| `Authorization` value | Expected |
|-----------------------|----------|
| `Bearer not.a.jwt` | `401` |
| `Bearer` (scheme only, no credential) | `401` |
| `Basic dXNlcjpwYXNz` (wrong scheme) | `401` |

> A literally empty credential (`"Bearer "` with a trailing space) can't be sent
> by a spec-compliant HTTP client — httpx rejects it as an illegal header value —
> so the "no credential" class is exercised with the scheme alone.
| `<valid token without "Bearer ">` | `401` |

### TC-AUTH-13 — Tampered / wrong-secret token → 401 · P1 · EG/security
**Steps:** take a valid token and (a) flip a character in the signature, or
(b) present a token signed with a different secret.
**Expected:** `401` in both cases — the signature check fails; a token the
server did not sign is never trusted.

### TC-AUTH-14 — Round-trip consistency · P1 · ST
**Steps:** register `E`/`P` → login → `/me`.
**Expected:** `/me.email == E`, `/me.tier == "free"`, `/me.id ==` the id
returned by register. The identity survives the register→login→authenticated-read
sequence.

### TC-AUTH-15 — Password / hash never returned · P1 · security
**Steps:** inspect the bodies of register (`201`) and `/me` (`200`).
**Expected:** neither contains `password`, `hashed_password`, or any
password-like field. Enforced structurally by the test-side `UserOut`
(`extra="forbid"`) — an extra field fails the shape assertion.
