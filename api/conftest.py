"""API-suite-specific fixtures (config-dependent seed tests).

The shared `api` client, `canary` and Allure hook live in the root conftest
(they serve both suites). These fixtures are API-only: they probe the seed
endpoint's server configuration and skip tests whose required mode does not
match — see test-cases/02-admin-seed.md.
"""

import os

import httpx
import pytest


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
