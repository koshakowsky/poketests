"""E2E fixtures: web base URL, Page Objects, and programmatic login.

The `page` fixture comes from pytest-playwright (browser matrix via `--browser`).
The root poketests/conftest.py still applies here - its canary (SUT healthy +
Gen I dataset) is a valid precondition for the UI too, and its Allure-metadata
hook gives E2E tests the same severity/feature labels.

Premium journeys don't re-walk the login/checkout UI every time: a user is
created (and, for premium, upgraded) via the API, then its JWT is injected into
the SPA's localStorage before navigation - see `browser_login`. Tokens come from
the shared `fixtures.users` plugin.
"""

import json
import os

import pytest

# The `pages` package is importable via pytest's `pythonpath = e2e` (pytest.ini).
from pages.account_page import AccountPage
from pages.analytics_page import AnalyticsPage
from pages.checkout_page import CheckoutPage
from pages.compare_page import ComparePage
from pages.login_page import LoginPage
from pages.search_page import SearchPage
from pages.similar_page import SimilarPage

TOKEN_KEY = "poke_token"  # matches the SPA (frontend/src/api/client.ts)


@pytest.fixture(scope="session")
def base_url() -> str:
    # Frontend origin (nginx serves the SPA and proxies /api). Distinct from
    # POKETESTS_BASE_URL, which the API suite uses for the /api client.
    return os.getenv("POKETESTS_WEB_URL", "http://localhost")


def _inject_token(page, token: str) -> None:
    # Seed the token before any app JS runs, so the auth context hydrates from
    # it on the next navigation (persists across route changes and reloads).
    page.add_init_script(
        f"window.localStorage.setItem({json.dumps(TOKEN_KEY)}, {json.dumps(token)});"
    )


@pytest.fixture
def browser_login(page):
    """Factory: inject a bearer token into the browser session, return the page."""
    def _login(token: str):
        _inject_token(page, token)
        return page
    return _login


@pytest.fixture
def premium_browser(page, premium_token):
    """A shared, read-only premium session (do not cancel its subscription)."""
    _inject_token(page, premium_token)
    return page


@pytest.fixture
def free_browser(page, make_user):
    """A fresh, logged-in free session."""
    _inject_token(page, make_user().token)
    return page


# Public page - no auth.
@pytest.fixture
def search_page(page, base_url) -> SearchPage:
    return SearchPage(page, base_url)


# Premium pages - authenticated read-only session.
@pytest.fixture
def compare_page(premium_browser, base_url) -> ComparePage:
    return ComparePage(premium_browser, base_url)


@pytest.fixture
def analytics_page(premium_browser, base_url) -> AnalyticsPage:
    return AnalyticsPage(premium_browser, base_url)


@pytest.fixture
def similar_page(premium_browser, base_url) -> SimilarPage:
    return SimilarPage(premium_browser, base_url)


# Auth / billing pages - plain page; tests inject a token via browser_login,
# free_browser or premium_browser (all share the same `page`) when needed.
@pytest.fixture
def login_page(page, base_url) -> LoginPage:
    return LoginPage(page, base_url)


@pytest.fixture
def checkout_page(page, base_url) -> CheckoutPage:
    return CheckoutPage(page, base_url)


@pytest.fixture
def account_page(page, base_url) -> AccountPage:
    return AccountPage(page, base_url)
