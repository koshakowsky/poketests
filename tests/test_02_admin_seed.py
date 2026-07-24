"""Admin/Seed — test-cases/02-admin-seed.md

Architecture: the endpoint's behavior depends on the SERVER CONFIGURATION
(SEED_TOKEN), so tests declare the required mode via the seed_disabled/
seed_enabled markers, and the actual stage mode is detected by a probe (the
seed_mode fixture in conftest). The CI matrix brings the stage up in both
modes — see .github/workflows/api-tests.yml.

Validation cases (422) are config-independent: FastAPI validates query
parameters BEFORE the handler code, i.e. before the token check — so they
run in any job.
"""

import time

import pytest


@pytest.mark.p0
@pytest.mark.seed_disabled
def test_seed_disabled_without_server_token(api):
    """TC-SEED-01 (DT row 1): SEED_TOKEN not set -> 403 for everyone."""
    r = api.post("admin/seed")
    assert r.status_code == 403
    assert r.json()["detail"] == "Seeding is disabled"


@pytest.mark.p1
@pytest.mark.seed_enabled
def test_seed_rejects_missing_header(api):
    """TC-SEED-02 (DT row 2): token configured, header absent -> 401."""
    r = api.post("admin/seed")
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid seed token"


@pytest.mark.p1
@pytest.mark.seed_enabled
@pytest.mark.parametrize(
    "token",
    ["wrong-token", ""],
    ids=["wrong", "empty-string"],
)
def test_seed_rejects_invalid_token(api, token):
    """TC-SEED-03 + TC-SEED-07: wrong and EMPTY header value -> 401.

    An empty string is a distinct class from "header absent": the header is
    sent, but the value "" does not match the token. A classic hole that
    `if token: ...`-style checks slip through.
    """
    r = api.post("admin/seed", headers={"X-Seed-Token": token})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid seed token"


@pytest.mark.p1
@pytest.mark.parametrize(
    "max_pokemon",
    [0, 1026, -5],
    ids=["below-min", "above-max", "negative"],
)
def test_seed_max_pokemon_out_of_range(api, max_pokemon):
    """TC-SEED-04 (a/d/e): max_pokemon bounds (ge=1, le=1025); config-independent."""
    assert api.post("admin/seed", params={"max_pokemon": max_pokemon}).status_code == 422


@pytest.mark.p2
def test_seed_max_pokemon_non_numeric(api):
    """TC-SEED-06: non-numeric max_pokemon -> 422; config-independent."""
    assert api.post("admin/seed", params={"max_pokemon": "abc"}).status_code == 422


@pytest.mark.p1
@pytest.mark.restricted
@pytest.mark.seed_enabled
def test_seed_run_populates_database(api, seed_token):
    """TC-SEED-05 (DT row 4): a correct token starts real seeding.

    DESTRUCTIVE + external network (PokeAPI): excluded from the default run
    (restricted marker), executed on an isolated stage with an empty DB and
    POKETESTS_SKIP_DATA_CANARY=1 (the data canary requires 151, but here the
    DB is empty by design).

    The ST-check oracle is polling with a deadline, not a fixed sleep: a
    background task is not obligated to finish within a guessed number of
    seconds.
    """
    total_before = api.get("pokemon/", params={"limit": 1}).json()["total"]
    if total_before:
        pytest.skip(
            f"DB already holds {total_before} records — this test is designed "
            f"for an empty isolated stage (otherwise the 'data appeared' oracle "
            f"is blind)"
        )

    r = api.post(
        "admin/seed",
        params={"max_pokemon": 5},
        headers={"X-Seed-Token": seed_token},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "background_task_started"
    assert "5" in body["message"]

    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        total = api.get("pokemon/", params={"limit": 1}).json()["total"]
        if total >= 5:
            break
        time.sleep(3)
    else:
        pytest.fail("background seeding did not produce 5 records within 180 seconds")

    # Spot-check the content, not just the counter
    assert api.get("pokemon/1").json()["name"] == "bulbasaur"
