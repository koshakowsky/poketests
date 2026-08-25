import os
import re

import allure
import httpx
import pytest
from allure_commons.types import Severity

from dataset import PROFILE
from fixtures import endpoint_coverage

pytest_plugins = ["fixtures.users"]   # fixtures.billing holds builders, not fixtures

BASE_URL = os.getenv("POKETESTS_BASE_URL", "http://localhost/api")

SKIP_DATA_CANARY = os.getenv("POKETESTS_SKIP_DATA_CANARY") == "1"

SEVERITY_BY_PRIORITY = {
    "p0": Severity.BLOCKER,
    "p1": Severity.CRITICAL,
    "p2": Severity.NORMAL,
    "p3": Severity.MINOR,
}


TC_ID_PATTERN = re.compile(r"(?:TC|E2E)-[A-Z][A-Z0-9]*-\d+")

LAYER_BY_DIR = {"api": "API", "e2e": "E2E", "contract": "Contract"}


def pytest_collection_modifyitems(items):
    for item in items:
        for priority, severity in SEVERITY_BY_PRIORITY.items():
            if item.get_closest_marker(priority):
                item.add_marker(allure.severity(severity))
                break

        layer = LAYER_BY_DIR.get(item.nodeid.split("/", 1)[0])
        if layer:
            item.add_marker(allure.parent_suite(layer))

        module = item.module.__name__.removeprefix("test_")
        feature = module.replace("_", " ").capitalize()
        item.add_marker(allure.feature(feature))

        for tc_id in TC_ID_PATTERN.findall(item.function.__doc__ or ""):
            item.add_marker(allure.tag(tc_id))


@pytest.fixture(scope="session")
def api() -> httpx.Client:
    with endpoint_coverage.client(
        base_url=BASE_URL.rstrip("/") + "/",
        timeout=10.0,
        follow_redirects=False,
    ) as client:
        yield client


@pytest.fixture(scope="session", autouse=True)
def canary(api: httpx.Client) -> None:
    """TC-ENV-01, TC-ENV-02, TC-ENV-03: run entry criteria (fail-fast).

    Implemented as a session fixture rather than as tests on purpose: a broken
    precondition invalidates the whole run, so it must abort before the suite
    instead of adding three more red results to dozens of noisy failures. The
    trade-off is that these IDs carry no Allure tag - they are gate, not case.
    """
    try:
        health = api.get("health")
    except httpx.HTTPError as exc:
        pytest.exit(f"[canary] SUT is unavalible in {BASE_URL}: {exc}", returncode=2)
    if health.status_code != 200 or health.json().get("status") != "ok":
        pytest.exit(
            f"[canary] health returned {health.status_code}: {health.text[:200]}",
            returncode=2,
        )

    if not SKIP_DATA_CANARY:
        listing = api.get("pokemon/", params={"limit": 1})
        total = listing.json().get("total") if listing.status_code == 200 else None
        if total != PROFILE.total:
            pytest.exit(
                f"[canary] {total} pokemons in DB, the active dataset profile "
                f"'{PROFILE.name}' is wating {PROFILE.total} (fixture "
                f"{PROFILE.sut_fixture}). The test-run has been stopped",
                returncode=2,
            )

    openapi = api.get("openapi.json")
    try:
        schema_ok = (
            openapi.status_code == 200
            and openapi.headers.get("content-type", "").startswith("application/json")
            and "paths" in openapi.json()
        )
    except ValueError:
        schema_ok = False
    if schema_ok:
        endpoint_coverage.record_documented(openapi.json())

    if not schema_ok:
        import warnings

        warnings.warn(
            f"[canary] /api/openapi.json invalid schema "
            f"(status={openapi.status_code}, "
            f"content-type={openapi.headers.get('content-type')})"
        )


def pytest_sessionfinish(session):
    """Persist measured endpoint coverage alongside the Allure results."""
    endpoint_coverage.write(session.config)
