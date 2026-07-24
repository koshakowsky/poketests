"""Health — test-cases/01-health.md"""

import pytest

from schemas import HealthResponse


@pytest.mark.p0
def test_health_returns_ok(api):
    """TC-HLT-01: health response is 200 and status=ok."""
    r = api.get("health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.p1
def test_health_body_fields(api):
    """TC-HLT-02: health body contract (shape-test).
    full validation
    """
    r = api.get("health")
    assert r.headers["content-type"].startswith("application/json")
    body = HealthResponse.model_validate(r.json())
    assert body.service


@pytest.mark.p3
def test_health_post_not_allowed(api):
    """TC-HLT-03: method not allowed -> 405."""
    assert api.post("health").status_code == 405
