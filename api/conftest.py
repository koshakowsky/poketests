"""API-suite-specific fixtures.

Everything shared lives elsewhere on purpose: the api client, canary and Allure
hook in the root conftest, identity fixtures in fixtures/users.py (registered
as a plugin). What stays here is API-only - probes and secrets that no other
suite has any use for.
"""

import os

import httpx
import pytest


@pytest.fixture(scope="session")
def jwt_secret() -> str:
    """The SUT's JWT signing secret, needed to forge signed-but-expired tokens
    (TC-SEC-03). Skips when unset, mirroring the seed_token pattern."""
    secret = os.getenv("POKETESTS_JWT_SECRET")
    if not secret:
        pytest.skip("POKETESTS_JWT_SECRET not set - signed-token forgery unavailable.")
    return secret


@pytest.fixture(scope="session")
def seed_mode(api: httpx.Client) -> str:
    """SUT configuration probe: 'disabled' | 'enabled' (session-cached).

    The seed endpoint's behaviour depends on server config a test cannot change,
    so the config becomes an explicit axis: probe it once, skip what does not fit.
    """
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
        pytest.skip("POKETESTS_SEED_TOKEN is not set - positive seed test is unavailable.")
    return token
