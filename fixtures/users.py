import uuid
from datetime import datetime, timezone

import httpx
import pytest

from dataset import ADMIN, CARDS


def future_expiry() -> tuple[int, int]:
    return 12, datetime.now(timezone.utc).year + 2


class User:
    def __init__(self, email: str, password: str, token: str):
        self.email = email
        self.password = password
        self.token = token

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}


def _login(api, email, password) -> httpx.Response:
    return api.post("auth/login", json={"email": email, "password": password})


def _register_and_login(api, email, password) -> str:
    api.post("auth/register", json={"email": email, "password": password})
    r = _login(api, email, password)
    r.raise_for_status()
    return r.json()["access_token"]


def _checkout_premium(api, token) -> None:
    month, year = future_expiry()
    r = api.post(
        "billing/checkout",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "plan_id": "premium",
            "card": {"number": CARDS.visa_ok, "exp_month": month, "exp_year": year, "cvc": "123"},
        },
    )
    r.raise_for_status()


@pytest.fixture
def auth_headers():
    return lambda token: {"Authorization": f"Bearer {token}"}


@pytest.fixture
def make_user(api):
    def _make(password: str = "password123") -> User:
        email = f"user+{uuid.uuid4().hex}@test.io"
        return User(email, password, _register_and_login(api, email, password))
    return _make


@pytest.fixture
def free_user(make_user) -> User:
    return make_user()


@pytest.fixture
def free_token(free_user) -> str:
    return free_user.token


@pytest.fixture(scope="session")
def admin_token(api) -> str:
    r = _login(api, ADMIN.email, ADMIN.password)
    if r.status_code != 200:
        pytest.skip(f"admin login failed ({r.status_code}) — admin not seeded on this stage")
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def premium_token(api) -> str:
    # A dedicated premium user, shared read-only across the suite. Tests that
    # mutate a subscription (cancel, re-subscribe) must use their own make_user.
    email = f"premium+{uuid.uuid4().hex}@test.io"
    token = _register_and_login(api, email, "password123")
    _checkout_premium(api, token)
    return token


@pytest.fixture(scope="session")
def premium_api(api, premium_token):
    with httpx.Client(
        base_url=api.base_url,
        timeout=10.0,
        follow_redirects=False,
        headers={"Authorization": f"Bearer {premium_token}"},
    ) as client:
        yield client
