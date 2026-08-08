"""API-suite-specific fixtures (config-dependent seed tests).

The shared `api` client, `canary` and Allure hook live in the root conftest
(they serve both suites). These fixtures are API-only: they probe the seed
endpoint's server configuration and skip tests whose required mode does not
match — see test-cases/02-admin-seed.md.
"""

import os
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest

# ── Auth / billing fixtures ──────────────────────────────────────────
# Data-isolation strategy (see test-cases/api README): unique users per test,
# no per-test cleanup — the hermetic stack is torn down after the run, and there
# is no delete API to reach through (we stay black-box over HTTP). Unique emails
# keep tests independent, re-runnable and safe under pytest-xdist.

DEFAULT_PASSWORD = "password123"


def unique_email() -> str:
    """A fresh, collision-proof address per call (parallel-safe)."""
    return f"poketest+{uuid.uuid4().hex}@test.io"


def valid_card(number: str, cvc: str = "123") -> dict:
    """A card body with a safely-future expiry (computed from the run date)."""
    return {
        "number": number,
        "exp_month": 12,
        "exp_year": datetime.now(timezone.utc).year + 3,
        "cvc": cvc,
    }


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(api: httpx.Client, email: str, password: str) -> str:
    r = api.post("auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _client_with_token(api: httpx.Client, token: str) -> httpx.Client:
    """A client sharing the base config of `api` but sending a bearer token.
    Base URL/timeout are reused from `api` so config stays single-sourced."""
    return httpx.Client(
        base_url=api.base_url,
        timeout=api.timeout,
        follow_redirects=False,
        headers=_bearer(token),
    )


@pytest.fixture
def new_user(api: httpx.Client) -> SimpleNamespace:
    """Register a fresh free user (function-scope — isolated per test)."""
    email = unique_email()
    r = api.post("auth/register", json={"email": email, "password": DEFAULT_PASSWORD})
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    return SimpleNamespace(email=email, password=DEFAULT_PASSWORD, id=r.json()["id"])


@pytest.fixture
def user_token(api: httpx.Client, new_user: SimpleNamespace) -> str:
    return _login(api, new_user.email, new_user.password)


@pytest.fixture
def free_client(api: httpx.Client, user_token: str):
    """Authenticated client for a free-tier user."""
    with _client_with_token(api, user_token) as client:
        yield client


@pytest.fixture
def premium_user(api: httpx.Client, new_user: SimpleNamespace) -> SimpleNamespace:
    """A registered user upgraded to premium via a real (fake-gateway) checkout."""
    from dataset import CARDS

    token = _login(api, new_user.email, new_user.password)
    r = api.post(
        "billing/checkout",
        json={"plan_id": "premium", "card": valid_card(CARDS.visa_ok)},
        headers=_bearer(token),
    )
    assert r.status_code == 200, f"checkout failed: {r.status_code} {r.text}"
    return SimpleNamespace(email=new_user.email, password=new_user.password,
                           id=new_user.id, token=token)


@pytest.fixture
def premium_client(api: httpx.Client, premium_user: SimpleNamespace):
    """Authenticated client for a premium-tier user (analytics/compare/similar)."""
    with _client_with_token(api, premium_user.token) as client:
        yield client


@pytest.fixture(scope="session")
def admin_token(api: httpx.Client) -> str:
    """Token for the SUT's bootstrapped admin (session-cached — read-only use)."""
    email = os.getenv("POKETESTS_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("POKETESTS_ADMIN_PASSWORD", "admin-password-123")
    r = api.post("auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        pytest.skip(
            f"admin login failed ({r.status_code}) — set POKETESTS_ADMIN_EMAIL/"
            f"PASSWORD to match the SUT's seeded admin"
        )
    return r.json()["access_token"]


@pytest.fixture
def admin_client(api: httpx.Client, admin_token: str):
    with _client_with_token(api, admin_token) as client:
        yield client


@pytest.fixture(scope="session")
def jwt_secret() -> str:
    """The SUT's JWT signing secret — needed to forge signed-but-expired tokens
    (TC-SEC-03). Skips when unset, mirroring the seed_token pattern."""
    secret = os.getenv("POKETESTS_JWT_SECRET")
    if not secret:
        pytest.skip("POKETESTS_JWT_SECRET not set — signed-token forgery unavailable.")
    return secret


@pytest.fixture(scope="session")
def seed_mode(api: httpx.Client) -> str:
    """SUT configuration probe: 'disabled' | 'enabled' (session-cached)."""
    status = api.post("admin/seed").status_code
    modes = {403: "disabled", 401: "enabled"}
    if status not in modes:
        pytest.fail(
            f"[seed-probe] unexpected status {status}: failed to determine "
            f"the seed endpoint mode"
        )
    return modes[status]


@pytest.fixture(autouse=True)
def _seed_mode_gate(request):
    """Auto-skip tests whose required seed mode does not match the actual one."""
    if request.node.get_closest_marker("seed_disabled"):
        required = "disabled"
    elif request.node.get_closest_marker("seed_enabled"):
        required = "enabled"
    else:
        return
    actual = request.getfixturevalue("seed_mode")
    if actual != required:
        pytest.skip(f"stage in seed={actual} mode, this test needs seed={required}")


@pytest.fixture(scope="session")
def seed_token() -> str:
    token = os.getenv("POKETESTS_SEED_TOKEN")
    if not token:
        pytest.skip("POKETESTS_SEED_TOKEN is not set — positive seed test is unavailable.")
    return token
