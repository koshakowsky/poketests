# E2E · Authentication

Login / register / logout journeys and the route guard that redirects
unauthenticated users. Business rules (credential validation, tiers) are
covered at the API layer ([10-auth.md](../api/10-auth.md),
[12-rbac.md](../api/12-rbac.md)); these cases verify only what the **browser**
does — forms, header state, routing, session persistence.

**Pages / testids:** `/login` (`login-page`, `auth-email`, `auth-password`,
`auth-submit`, `auth-toggle`, `auth-error`); header (`login-link`,
`user-email`, `user-tier`, `logout-button`).

| ID | Title | Prio | Kind |
|----|-------|------|------|
| E2E-AUTH-01 | Register a new account (journey) | P0 | journey *(matrix)* |
| E2E-AUTH-02 | Log in with an existing account | P0 | journey *(matrix)* |
| E2E-AUTH-03 | Anonymous → premium page redirects to /login | P0 | routing *(matrix)* |
| E2E-AUTH-04 | Invalid login shows an error | P1 | negative |
| E2E-AUTH-05 | Log out clears the session | P1 | journey |
| E2E-AUTH-06 | Post-login return to the intended page | P1 | journey |
| E2E-AUTH-07 | Session persists across reload | P1 | journey |
| E2E-AUTH-08 | Toggle login ⇄ register | P2 | render |

---

### E2E-AUTH-01 — Register a new account · P0 · journey *(matrix)*
**Steps:** open `/login`; click `auth-toggle` (→ register mode); fill
`auth-email` with a unique address and `auth-password` (≥8 chars); submit.
**Expected:** lands on `/` logged in; the header shows `user-email` with the
address and `user-tier` reading `FREE`; `login-link` is gone. (Register
auto-logs-in — no second step.)

### E2E-AUTH-02 — Log in with an existing account · P0 · journey *(matrix)*
**Precondition:** an account exists (created via API in a fixture).
**Steps:** open `/login`; fill credentials; submit.
**Expected:** header shows `user-email`; `logout-button` visible.

### E2E-AUTH-03 — Anonymous → premium page redirects · P0 · routing *(matrix)*
**Steps:** without logging in, navigate directly to `/analytics`.
**Expected:** the app redirects to `/login` (`login-page` visible); the
analytics grid never renders. Mirrors the API `401` for anonymous premium
access — expressed in the UI as a redirect to sign in.

### E2E-AUTH-04 — Invalid login shows an error · P1 · negative
**Steps:** open `/login`; enter a registered email with a **wrong** password;
submit.
**Expected:** `auth-error` becomes visible ("Invalid email or password."); the
user stays on `/login`; no session is created (`login-link` still absent from a
logged-in header — i.e. header shows the logged-out state).

### E2E-AUTH-05 — Log out clears the session · P1 · journey
**Precondition:** logged in.
**Steps:** click `logout-button`.
**Expected:** header returns to the logged-out state (`login-link` visible,
`user-email` gone); navigating to `/analytics` now redirects to `/login`.

### E2E-AUTH-06 — Post-login return to intended page · P1 · journey
**Steps:** anonymous, navigate to `/compare` → redirected to `/login`; log in.
**Expected:** after login the app lands back on `/compare` (the guard preserved
the intended destination), not on `/`.

### E2E-AUTH-07 — Session persists across reload · P1 · journey
**Steps:** log in; reload the page.
**Expected:** still logged in (header shows `user-email`) — the token is
restored from `localStorage` and `/me` re-hydrates the session. A brief
`auth-loading` state is acceptable before the header settles.

### E2E-AUTH-08 — Toggle login ⇄ register · P2 · render
**Steps:** on `/login`, click `auth-toggle` repeatedly.
**Expected:** the title switches between "Welcome back" and "Create account" and
the submit label between "Log in" and "Sign up"; a prior `auth-error` clears on
toggle.
