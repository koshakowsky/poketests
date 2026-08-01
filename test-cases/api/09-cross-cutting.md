# Cross-cutting — CORS, routing, non-functional smoke

Checks that span endpoints rather than belonging to one.

**CORS context:** the server is configured with an **explicit** origin list
(env `CORS_ORIGINS`, defaults: `http://localhost`, `http://localhost:3000`,
`http://localhost:8000`) with `allow_credentials=true`. A wildcard is invalid
in this combination.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-XC-01 | CORS: preflight with an allowed origin | P2 | EP |
| TC-XC-02 | CORS: foreign origin gets no allow headers | P2 | EP/EG |
| TC-XC-03 | Trailing slash: 307 redirect | P3 | EG |
| TC-XC-04 | Perf smoke: response time of key routes | P3 | non-functional |

---

### TC-XC-01 — Preflight with an allowed origin · P2 · EP
**Request:** `OPTIONS /api/pokemon/` with headers
`Origin: http://localhost:3000`, `Access-Control-Request-Method: GET`
**Expected:** `200`; `Access-Control-Allow-Origin: http://localhost:3000`;
`Access-Control-Allow-Credentials: true`.

### TC-XC-02 — Foreign origin is rejected · P2 · EP/EG
| Request | Expected |
|---------|----------|
| Preflight `OPTIONS /api/pokemon/` with `Origin: https://evil.example`, `Access-Control-Request-Method: GET` | the response does **not** contain `Access-Control-Allow-Origin` for the foreign origin (Starlette answers such a preflight with 400) |
| Simple `GET /api/health` with `Origin: https://evil.example` | `200` (request served), but no `Access-Control-Allow-Origin` header — the browser will not expose the response to the page |

### TC-XC-03 — Trailing slash · P3 · EG
Routes are declared with a trailing slash (`/api/pokemon/`). FastAPI serves
slash-less requests via a redirect — clients must be aware.
**Request:** `GET /api/pokemon` (no slash, **without** follow-redirects)
**Expected:** `307`; `Location` points to `/api/pokemon/`.
**Automation convention:** the test HTTP client uses canonical slashed paths
and does **not** follow redirects silently (follow_redirects=False), so such
discrepancies stay visible.

### TC-XC-04 — Perf smoke · P3 · non-functional
Informative test (not a release gate): flags performance regressions in the
local docker environment.
**Steps:** 20 sequential requests to `GET /api/health` and to
`GET /api/pokemon/?limit=50`; collect durations.
**Expected (soft thresholds):** p95 `health` < 200 ms; p95 of the listing
< 500 ms. A failure is a prompt to investigate, not a blocker.
