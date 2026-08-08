"""Auth — test-cases/10-auth.md"""

import uuid

import pytest

from schemas import TokenResponse, UserOut


def _email() -> str:
    return f"user+{uuid.uuid4().hex}@test.io"


@pytest.mark.p0
def test_register_new_user(api):
    """TC-AUTH-01: register -> 201, free tier, UserOut shape (no password leak)."""
    email = _email()
    r = api.post("auth/register", json={"email": email, "password": "password123"})
    assert r.status_code == 201
    body = UserOut.model_validate(r.json())
    assert body.email == email
    assert body.tier == "free"
    assert body.id > 0


@pytest.mark.p1
def test_register_duplicate_email(api):
    """TC-AUTH-02: same email twice -> 409."""
    email = _email()
    payload = {"email": email, "password": "password123"}
    assert api.post("auth/register", json=payload).status_code == 201
    dup = api.post("auth/register", json=payload)
    assert dup.status_code == 409
    assert dup.json()["detail"] == "Email already registered"


@pytest.mark.p1
@pytest.mark.parametrize(
    "password, expected",
    [("1234567", 422), ("12345678", 201), ("123456789", 201), ("", 422)],
    ids=["7-below", "8-lower-bound", "9-above", "empty"],
)
def test_register_password_length(api, password, expected):
    """TC-AUTH-03: BVA on password min_length=8."""
    r = api.post("auth/register", json={"email": _email(), "password": password})
    assert r.status_code == expected


@pytest.mark.p1
@pytest.mark.parametrize(
    "payload",
    [{"password": "password123"}, {"email": "a@b.io"}, {}],
    ids=["no-email", "no-password", "empty"],
)
def test_register_invalid_body(api, payload):
    """TC-AUTH-04: missing required fields -> 422."""
    assert api.post("auth/register", json=payload).status_code == 422


@pytest.mark.p2
def test_register_email_format_not_validated(api):
    """TC-AUTH-05: documents actual — email is a plain str, so a malformed
    address is accepted (201). Pins the current contract; a future switch to
    EmailStr would flip this to 422 and this test would flag it."""
    r = api.post("auth/register", json={"email": "not-an-email", "password": "password123"})
    assert r.status_code == 201


@pytest.mark.p0
def test_login_returns_bearer_token(api, make_user):
    """TC-AUTH-06: valid credentials -> 200, TokenResponse, JWT shape."""
    user = make_user()
    r = api.post("auth/login", json={"email": user.email, "password": user.password})
    assert r.status_code == 200
    token = TokenResponse.model_validate(r.json())
    assert token.token_type == "bearer"
    assert token.access_token.count(".") == 2  # header.payload.signature


@pytest.mark.p0
def test_login_wrong_password(api, make_user):
    """TC-AUTH-07: correct email, wrong password -> 401."""
    user = make_user()
    r = api.post("auth/login", json={"email": user.email, "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


@pytest.mark.p1
def test_login_unknown_email_no_enumeration(api, make_user):
    """TC-AUTH-08: unknown email -> 401 with the SAME detail as a wrong password,
    so the two cases are indistinguishable (no user enumeration)."""
    user = make_user()
    wrong_pw = api.post("auth/login", json={"email": user.email, "password": "nope"})
    unknown = api.post("auth/login", json={"email": _email(), "password": "password123"})
    assert unknown.status_code == wrong_pw.status_code == 401
    assert unknown.json()["detail"] == wrong_pw.json()["detail"]


@pytest.mark.p0
def test_me_with_valid_token(api, make_user, auth_headers):
    """TC-AUTH-10: /me with a bearer token -> 200, matching user."""
    user = make_user()
    r = api.get("auth/me", headers=auth_headers(user.token))
    assert r.status_code == 200
    body = UserOut.model_validate(r.json())
    assert body.email == user.email
    assert body.tier == "free"


@pytest.mark.p0
def test_me_without_token(api):
    """TC-AUTH-11: no Authorization header -> 401 + WWW-Authenticate."""
    r = api.get("auth/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"
    assert r.headers.get("www-authenticate") == "Bearer"


@pytest.mark.p1
@pytest.mark.parametrize(
    "header",
    [
        {"Authorization": "Bearer not.a.jwt"},
        {"Authorization": "Bearer"},
        {"Authorization": "Basic dXNlcjpwYXNz"},
    ],
    ids=["garbage-jwt", "scheme-only", "wrong-scheme"],
)
def test_me_malformed_token(api, header):
    """TC-AUTH-12: malformed / wrong-scheme credentials -> 401."""
    assert api.get("auth/me", headers=header).status_code == 401


@pytest.mark.p1
def test_me_tampered_signature(api, make_user, auth_headers):
    """TC-AUTH-13: a valid token with a mangled signature -> 401 (a token the
    server did not sign is never trusted)."""
    user = make_user()
    tampered = user.token[:-4] + ("aaaa" if user.token[-4:] != "aaaa" else "bbbb")
    assert api.get("auth/me", headers=auth_headers(tampered)).status_code == 401


@pytest.mark.p1
def test_register_login_me_round_trip(api, make_user, auth_headers):
    """TC-AUTH-14: identity is stable across register -> login -> /me."""
    user = make_user()
    me = api.get("auth/me", headers=auth_headers(user.token)).json()
    assert me["email"] == user.email
    assert me["tier"] == "free"


@pytest.mark.p1
def test_password_never_returned(api, make_user, auth_headers):
    """TC-AUTH-15: no password/hash field in register or /me bodies."""
    user = make_user()
    reg = api.post("auth/register", json={"email": _email(), "password": "password123"}).json()
    me = api.get("auth/me", headers=auth_headers(user.token)).json()
    for body in (reg, me):
        assert "password" not in body
        assert "hashed_password" not in body
