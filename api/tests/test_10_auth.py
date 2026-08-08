"""Auth — test-cases/api/10-auth.md"""

import uuid

import pytest

from conftest import DEFAULT_PASSWORD, unique_email
from schemas import TokenResponse, UserOut


@pytest.mark.p0
def test_register_new_user(api):
    """TC-AUTH-01: register → 201, free tier, UserOut shape (no password leak)."""
    email = unique_email()
    r = api.post("auth/register", json={"email": email, "password": DEFAULT_PASSWORD})
    assert r.status_code == 201, r.text
    body = r.json()
    UserOut.model_validate(body)          # extra="forbid" → fails if hash leaks
    assert body["email"] == email
    assert body["tier"] == "free"
    assert body["id"] > 0


@pytest.mark.p1
def test_register_duplicate_email(api):
    """TC-AUTH-02: same email twice → 409."""
    email = unique_email()
    first = api.post("auth/register", json={"email": email, "password": DEFAULT_PASSWORD})
    assert first.status_code == 201, first.text
    second = api.post("auth/register", json={"email": email, "password": DEFAULT_PASSWORD})
    assert second.status_code == 409
    assert second.json()["detail"] == "Email already registered"


@pytest.mark.p1
@pytest.mark.parametrize(
    "password, expected",
    [
        ("1234567", 422),      # 7 — below min_length=8
        ("12345678", 201),     # 8 — lower bound
        ("123456789", 201),    # 9 — above
        ("", 422),             # empty
    ],
)
def test_register_password_length_boundary(api, password, expected):
    """TC-AUTH-03: password min_length=8 — BVA around the boundary."""
    r = api.post("auth/register", json={"email": unique_email(), "password": password})
    assert r.status_code == expected, r.text


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [
        {"password": DEFAULT_PASSWORD},     # no email
        {"email": "a@b.io"},                # no password
        {},                                 # empty
    ],
)
def test_register_invalid_body(api, body):
    """TC-AUTH-04: missing required fields → 422."""
    assert api.post("auth/register", json=body).status_code == 422


@pytest.mark.p2
def test_register_email_format_not_validated(api):
    """TC-AUTH-05: documents ACTUAL behavior — email is a plain str, not
    validated, so a syntactically invalid email is accepted (201)."""
    # Unique but still syntactically invalid (no @) → keeps the test re-runnable.
    invalid = f"not-an-email-{uuid.uuid4().hex}"
    r = api.post("auth/register", json={"email": invalid, "password": DEFAULT_PASSWORD})
    assert r.status_code == 201, r.text
    assert r.json()["email"] == invalid


@pytest.mark.p0
def test_login_happy(api, new_user):
    """TC-AUTH-06: valid credentials → 200 with a bearer JWT."""
    r = api.post("auth/login", json={"email": new_user.email, "password": new_user.password})
    assert r.status_code == 200, r.text
    body = r.json()
    TokenResponse.model_validate(body)
    assert body["token_type"] == "bearer"
    assert body["access_token"].count(".") == 2   # header.payload.signature


@pytest.mark.p0
def test_login_wrong_password(api, new_user):
    """TC-AUTH-07: correct email, wrong password → 401."""
    r = api.post("auth/login", json={"email": new_user.email, "password": "wrong-password"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password"


@pytest.mark.p1
def test_login_unknown_email_no_enumeration(api, new_user):
    """TC-AUTH-08: unknown email → 401 with the SAME detail as a wrong password,
    so the two cases are indistinguishable (no user enumeration)."""
    unknown = api.post("auth/login", json={"email": unique_email(), "password": "whatever1"})
    wrong = api.post("auth/login", json={"email": new_user.email, "password": "wrong-password"})
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


@pytest.mark.p2
@pytest.mark.parametrize("body", [{"email": "a@b.io"}, {"password": "x"}, {}])
def test_login_invalid_body(api, body):
    """TC-AUTH-09: malformed login body → 422 (before any credential check)."""
    assert api.post("auth/login", json=body).status_code == 422


@pytest.mark.p0
def test_me_with_valid_token(free_client, new_user):
    """TC-AUTH-10: /me with a valid token → 200, matching user."""
    r = free_client.get("auth/me")
    assert r.status_code == 200, r.text
    body = r.json()
    UserOut.model_validate(body)
    assert body["email"] == new_user.email
    assert body["tier"] == "free"


@pytest.mark.p0
def test_me_without_token(api):
    """TC-AUTH-11: /me with no Authorization → 401 + WWW-Authenticate."""
    r = api.get("auth/me")
    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"
    assert r.headers.get("www-authenticate") == "Bearer"


@pytest.mark.p1
@pytest.mark.parametrize(
    "auth_header",
    [
        "Bearer not.a.jwt",
        "Bearer",                 # scheme only, no credential
        "Basic dXNlcjpwYXNz",     # wrong scheme
    ],
)
def test_me_malformed_token(api, auth_header):
    """TC-AUTH-12: malformed / garbage / wrong-scheme credentials → 401."""
    r = api.get("auth/me", headers={"Authorization": auth_header})
    assert r.status_code == 401


@pytest.mark.p1
def test_me_tampered_token(api, user_token):
    """TC-AUTH-13: flip a character in the signature → 401 (signature check)."""
    head, payload, sig = user_token.split(".")
    tampered_char = "A" if sig[-1] != "A" else "B"
    tampered = f"{head}.{payload}.{sig[:-1]}{tampered_char}"
    r = api.get("auth/me", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401


@pytest.mark.p1
def test_round_trip_consistency(api, new_user, free_client):
    """TC-AUTH-14: register → login → me is a consistent identity."""
    r = free_client.get("auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == new_user.email
    assert body["id"] == new_user.id
    assert body["tier"] == "free"


@pytest.mark.p1
def test_password_never_returned(api, free_client):
    """TC-AUTH-15: no password/hash field in register or /me bodies."""
    register = api.post("auth/register", json={"email": unique_email(), "password": DEFAULT_PASSWORD})
    me = free_client.get("auth/me")
    for body in (register.json(), me.json()):
        assert "password" not in body
        assert "hashed_password" not in body
