"""Identity fixtures: users, tokens and authenticated clients.

Registered as a plugin from the root conftest, so every suite gets them without
a star-import.

Data isolation is by construction rather than by cleanup: every user is created
with a unique email and nothing is torn down between tests. The suite stays
black-box over HTTP and the SUT exposes no delete endpoint, so uniqueness is
what keeps tests independent, re-runnable, and safe to run in parallel against
one shared stack.
"""

import uuid
from dataclasses import dataclass

import httpx
import pytest

from dataset import ADMIN
from fixtures.billing import build_card

DEFAULT_PASSWORD = "password123"


def unique_email(prefix: str = "user") -> str:
    return f"{prefix}+{uuid.uuid4().hex}@test.io"


@dataclass(frozen=True)
class User:
    id: int
    email: str
    password: str
    token: str

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}


def _register(api, email: str, password: str) -> int:
    r = api.post("auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, f"register failed: {r.status_code} {r.text}"
    return r.json()["id"]


def _login(api, email: str, password: str) -> httpx.Response:
    return api.post("auth/login", json={"email": email, "password": password})


def _token(api, email: str, password: str) -> str:
    r = _login(api, email, password)
    r.raise_for_status()
    return r.json()["access_token"]


def _new_user(api, password: str = DEFAULT_PASSWORD, prefix: str = "user") -> User:
    email = unique_email(prefix)
    user_id = _register(api, email, password)
    return User(user_id, email, password, _token(api, email, password))


def _upgrade_to_premium(api, token: str) -> None:
    r = api.post(
        "billing/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={"plan_id": "premium", "card": build_card()},
    )
    r.raise_for_status()


@pytest.fixture
def auth_headers():
    return lambda token: {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(api):
    def _make(password: str = DEFAULT_PASSWORD) -> User:
        return _new_user(api, password)

    return _make


@pytest.fixture
def free_user(make_user) -> User:
    return make_user()


@pytest.fixture
def free_token(free_user) -> str:
    return free_user.token


@pytest.fixture
def make_premium_user(api, make_user):
    """A fresh user already upgraded through checkout.

    Use this whenever a test MUTATES the subscription (cancel, re-subscribe);
    the session-scoped premium_token must stay read-only.
    """

    def _make() -> User:
        user = make_user()
        _upgrade_to_premium(api, user.token)
        return user

    return _make


@pytest.fixture(scope="session")
def admin_token(api) -> str:
    """Token for the SUT's bootstrapped admin. Credentials come from
    dataset.ADMIN so the stage configuration lives in one place."""
    r = _login(api, ADMIN.email, ADMIN.password)
    if r.status_code != 200:
        pytest.skip(
            f"admin login failed ({r.status_code}) - set POKETESTS_ADMIN_EMAIL/PASSWORD "
            f"to match the SUT's seeded admin"
        )
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def premium_token(api) -> str:
    # One premium user per session, shared read-only. Session scope keeps the
    # checkout round-trip off every premium test; make_premium_user covers the
    # tests that need to change a subscription.
    user = _new_user(api, prefix="premium")
    _upgrade_to_premium(api, user.token)
    return user.token


@pytest.fixture(scope="session")
def premium_api(api, premium_token):
    with httpx.Client(
        base_url=api.base_url,
        timeout=api.timeout,
        follow_redirects=False,
        headers={"Authorization": f"Bearer {premium_token}"},
    ) as client:
        yield client
