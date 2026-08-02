"""E2E fixtures: web base URL + Page Object instances.

The `page` fixture comes from pytest-playwright (browser matrix via
`--browser`). The root poketests/conftest.py still applies here — its canary
(SUT healthy + Gen I dataset) is a valid precondition for the UI too, and its
Allure-metadata hook gives E2E tests the same severity/feature labels.
"""

import os

import pytest

# The `pages` package is importable via pytest's `pythonpath = e2e` (pytest.ini).
from pages.analytics_page import AnalyticsPage
from pages.compare_page import ComparePage
from pages.search_page import SearchPage
from pages.similar_page import SimilarPage


@pytest.fixture(scope="session")
def base_url() -> str:
    # Frontend origin (nginx serves the SPA and proxies /api). Distinct from
    # POKETESTS_BASE_URL, which the API suite uses for the /api client.
    return os.getenv("POKETESTS_WEB_URL", "http://localhost")


@pytest.fixture
def search_page(page, base_url) -> SearchPage:
    return SearchPage(page, base_url)


@pytest.fixture
def compare_page(page, base_url) -> ComparePage:
    return ComparePage(page, base_url)


@pytest.fixture
def analytics_page(page, base_url) -> AnalyticsPage:
    return AnalyticsPage(page, base_url)


@pytest.fixture
def similar_page(page, base_url) -> SimilarPage:
    return SimilarPage(page, base_url)
