# Health — `GET /api/health`

The simplest endpoint; used as the SUT availability smoke check and as the
docker-compose healthcheck dependency.

| ID | Title | Prio | Technique |
|----|-------|------|-----------|
| TC-HLT-01 | Health returns 200 and status ok | P0 | EP (happy) |
| TC-HLT-02 | Body contains the expected fields | P1 | EP |
| TC-HLT-03 | Non-GET method is not allowed | P3 | EG |

---

### TC-HLT-01 — Health returns 200 and status ok · P0 · EP
**Request:** `GET /api/health`
**Expected:**
- status `200`;
- `body.status == "ok"`.

### TC-HLT-02 — Body contains the expected fields · P1 · EP
**Request:** `GET /api/health`
**Expected:**
- `Content-Type: application/json`;
- keys `status` and `service` are present;
- `body.service` is a non-empty string (contains "PokéAnalytics").

### TC-HLT-03 — Unsupported method · P3 · EG
**Request:** `POST /api/health`
**Expected:**
- status `405 Method Not Allowed` (the route is declared GET-only).
