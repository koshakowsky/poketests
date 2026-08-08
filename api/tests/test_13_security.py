"""Security — test-cases/api/13-security.md

Application-layer security checks. Transport (TLS), rate-limiting and proxy
headers are out of scope here — see the file's "Scope & boundary".
"""

import base64
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from conftest import DEFAULT_PASSWORD, unique_email

PREMIUM_ENDPOINT = "analytics/type-distribution"


# ── tiny JWT forgers (stdlib only, no pyjwt dependency in the test suite) ──

def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _segment(obj: dict) -> str:
    return _b64url(json.dumps(obj, separators=(",", ":")).encode())


def forge_alg_none(sub: str = "1") -> str:
    """An unsigned token declaring alg:none, empty signature segment."""
    return f'{_segment({"alg": "none", "typ": "JWT"})}.{_segment({"sub": sub})}.'


def forge_hs256(secret: str, payload: dict) -> str:
    """A properly HS256-signed token (used to craft a valid-but-expired one)."""
    head = _segment({"alg": "HS256", "typ": "JWT"})
    body = _segment(payload)
    signing_input = f"{head}.{body}".encode()
    sig = _b64url(hmac.new(secret.encode(), signing_input, hashlib.sha256).digest())
    return f"{head}.{body}.{sig}"


# ── TC-SEC-01 — mass assignment / privilege escalation ──

@pytest.mark.p0
@pytest.mark.parametrize(
    "extra",
    [
        {"tier": "admin"},
        {"tier": "premium"},
        {"is_admin": True},
    ],
)
def test_no_privilege_escalation_via_register(api, extra):
    """TC-SEC-01: extra fields in the register body are ignored — tier stays free."""
    body = {"email": unique_email(), "password": DEFAULT_PASSWORD, **extra}
    r = api.post("auth/register", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["tier"] == "free"


@pytest.mark.p0
def test_injected_id_is_ignored(api):
    """TC-SEC-01: a client-supplied id is not honored — id is server-assigned."""
    r = api.post("auth/register", json={"email": unique_email(), "password": DEFAULT_PASSWORD, "id": 1})
    assert r.status_code == 201, r.text
    # id 1 is the seeded admin; a fresh user must never collide with it.
    assert r.json()["id"] != 1


@pytest.mark.p0
def test_escalation_has_no_effect_end_to_end(api):
    """TC-SEC-01: even after trying to self-assign admin, the account is denied
    premium access (403) — the injected tier had no effect."""
    email = unique_email()
    reg = api.post("auth/register", json={"email": email, "password": DEFAULT_PASSWORD, "tier": "admin"})
    assert reg.status_code == 201, reg.text
    token = api.post("auth/login", json={"email": email, "password": DEFAULT_PASSWORD}).json()["access_token"]
    r = api.get(PREMIUM_ENDPOINT, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# ── TC-SEC-02 / 03 — JWT attacks ──

@pytest.mark.p1
def test_alg_none_token_rejected(api):
    """TC-SEC-02: an unsigned alg:none token is not accepted → 401."""
    r = api.get("auth/me", headers={"Authorization": f"Bearer {forge_alg_none()}"})
    assert r.status_code == 401


@pytest.mark.p1
def test_expired_token_rejected(api, jwt_secret):
    """TC-SEC-03: a correctly-signed but expired token → 401 (exp enforced).
    Requires POKETESTS_JWT_SECRET matching the SUT (else the fixture skips)."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    token = forge_hs256(jwt_secret, {"sub": "1", "exp": int(past.timestamp())})
    r = api.get("auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


@pytest.mark.p1
def test_valid_signed_token_is_accepted(api, jwt_secret, new_user):
    """TC-SEC-03 (control): the same forging path with a FUTURE exp is accepted,
    proving the expired-token rejection is about exp, not a broken signature."""
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    token = forge_hs256(jwt_secret, {"sub": str(new_user.id), "exp": int(future.timestamp())})
    r = api.get("auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == new_user.email


# ── TC-SEC-04 / 05 — injection ──

@pytest.mark.p1
@pytest.mark.parametrize(
    "email",
    [
        "' OR '1'='1",
        "admin@example.com'--",
        '"; DROP TABLE users;--',
    ],
)
def test_sql_injection_in_login_is_neutralized(api, email):
    """TC-SEC-04: SQL metacharacters in credentials are treated as data → 401,
    never 200 (auth bypass) and never 500 (query error)."""
    r = api.post("auth/login", json={"email": email, "password": "whatever1"})
    assert r.status_code == 401
    # And the users table is intact — a normal register still works afterwards.
    assert api.post("auth/register", json={"email": unique_email(), "password": DEFAULT_PASSWORD}).status_code == 201


@pytest.mark.p2
def test_injection_payload_stored_inertly(api):
    """TC-SEC-05: an HTML/script payload in email round-trips verbatim as data."""
    # Unique suffix keeps the payload intact while staying re-runnable.
    payload = f"<script>alert(1)</script>+{uuid.uuid4().hex}@x.io"
    reg = api.post("auth/register", json={"email": payload, "password": DEFAULT_PASSWORD})
    assert reg.status_code == 201, reg.text
    token = api.post("auth/login", json={"email": payload, "password": DEFAULT_PASSWORD}).json()["access_token"]
    me = api.get("auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == payload   # stored/returned literally, not executed


# ── TC-SEC-06 — no internal leakage ──

@pytest.mark.p2
def test_errors_do_not_leak_internals(api, new_user):
    """TC-SEC-06: error bodies expose only intended detail — no stack traces,
    file paths, SQL fragments or password hashes."""
    leak_markers = ("Traceback", "hashed_password", "site-packages", "sqlalchemy",
                    "/app/", ".py\", line")
    responses = [
        api.post("auth/register", json={"bad": "body"}),          # 422
        api.post("auth/login", json={"email": new_user.email, "password": "wrong"}),  # 401
        api.get("auth/me", headers={"Authorization": "Bearer garbage"}),  # 401
    ]
    for r in responses:
        assert r.status_code in (401, 422)
        text = r.text
        for marker in leak_markers:
            assert marker not in text, f"leak marker {marker!r} in {text[:200]}"
