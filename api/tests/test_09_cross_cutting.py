"""Cross-cutting - test-cases/09-cross-cutting.md

Checks that span endpoints rather than belonging to one: CORS, routing
conventions and a non-functional smoke.
"""

import time

import pytest

ALLOWED_ORIGIN = "http://localhost:3000"
FOREIGN_ORIGIN = "https://evil.example"


@pytest.mark.p2
def test_cors_preflight_allowed_origin(api):
    """TC-XC-01: preflight from a configured origin is granted."""
    r = api.request(
        "OPTIONS",
        "pokemon/",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert r.headers.get("access-control-allow-credentials") == "true"


@pytest.mark.p2
def test_cors_preflight_foreign_origin_gets_no_grant(api):
    """TC-XC-02: a foreign origin never receives an allow-origin grant.

    The oracle is the absence of `access-control-allow-origin`, not the status:
    Starlette answers a disallowed preflight with 400 but still emits generic
    allow-methods/credentials headers.
    """
    r = api.request(
        "OPTIONS",
        "pokemon/",
        headers={
            "Origin": FOREIGN_ORIGIN,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in r.headers


@pytest.mark.p2
def test_cors_simple_request_foreign_origin_is_served_but_not_exposed(api):
    """TC-XC-02: a simple cross-origin GET is served, but without the grant.

    CORS is enforced in the browser, not the server: the request still runs
    (200), yet with no allow-origin header the page cannot read the response.
    """
    r = api.get("health", headers={"Origin": FOREIGN_ORIGIN})
    assert r.status_code == 200
    assert "access-control-allow-origin" not in r.headers


@pytest.mark.p3
def test_trailing_slash_redirects(api):
    """TC-XC-03: a slash-less path redirects to the canonical slashed route.

    The session client uses follow_redirects=False on purpose, so the hop is
    visible instead of being silently followed.
    """
    r = api.get("pokemon")
    assert r.status_code == 307
    assert r.headers["location"].endswith("/api/pokemon/")


@pytest.mark.p3
@pytest.mark.parametrize(
    "path, params, budget_ms",
    [
        ("health", None, 200),
        ("pokemon/", {"limit": 50}, 500),
    ],
    ids=["health", "list-50"],
)
def test_perf_smoke(api, path, params, budget_ms):
    """TC-XC-04: p95 latency stays within a soft budget on the local stack.

    Informative, not a release gate. Warm-up requests are excluded so cold
    connection setup does not dominate a 20-request p95.
    """
    for _ in range(3):
        api.get(path, params=params)

    durations = []
    for _ in range(20):
        started = time.perf_counter()
        r = api.get(path, params=params)
        durations.append((time.perf_counter() - started) * 1000)
        assert r.status_code == 200

    durations.sort()
    p95 = durations[int(len(durations) * 0.95) - 1]
    assert p95 < budget_ms, (
        f"p95={p95 :.0f}ms over the {budget_ms}ms budget for {path} "
        f"(min={durations[0]:.0f} max={durations[-1]:.0f})"
    )
