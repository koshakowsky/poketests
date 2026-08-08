"""RBAC — test-cases/12-rbac.md"""

import pytest

from dataset import CARDS
from fixtures.users import future_expiry

# (method, path, json) for the three premium-gated endpoints.
PREMIUM_ENDPOINTS = [
    ("GET", "analytics/type-distribution", None),
    ("GET", "pokemon/1/similar", None),
    ("POST", "compare/", {"pokemon_ids": [1, 4]}),
]
PREMIUM_IDS = ["analytics", "similar", "compare"]


@pytest.mark.p0
@pytest.mark.parametrize(
    "path",
    ["health", "pokemon/", "pokemon/1", "types/", "billing/plans"],
)
def test_public_endpoints_anonymous(api, path):
    """TC-RBAC-01: public endpoints need no auth."""
    assert api.get(path).status_code == 200


@pytest.mark.p0
@pytest.mark.parametrize(
    "identity, expected",
    [("anon", 401), ("free", 403), ("premium", 200), ("admin", 200)],
)
@pytest.mark.parametrize("method, path, json_body", PREMIUM_ENDPOINTS, ids=PREMIUM_IDS)
def test_premium_access_matrix(api, request, auth_headers, identity, expected, method, path, json_body):
    """TC-RBAC-02/03/04/05/09: premium endpoints across every identity.

    anonymous -> 401 (unidentified), free -> 403 (identified, under-privileged),
    premium/admin -> 200 (admin outranks premium).
    """
    headers = {}
    if identity != "anon":
        headers = auth_headers(request.getfixturevalue(f"{identity}_token"))
    r = api.request(method, path, headers=headers, json=json_body)
    assert r.status_code == expected


@pytest.mark.p1
@pytest.mark.parametrize(
    "identity, expected",
    [("anon", 401), ("free", 403), ("premium", 403), ("admin", 200)],
)
def test_admin_endpoint_role_row(api, request, auth_headers, identity, expected):
    """TC-RBAC-06: /admin/users requires the admin tier."""
    headers = {}
    if identity != "anon":
        headers = auth_headers(request.getfixturevalue(f"{identity}_token"))
    assert api.get("admin/users", headers=headers).status_code == expected


@pytest.mark.p0
def test_401_vs_403_distinction(api, free_token, premium_token, auth_headers):
    """TC-RBAC-07: the crux — missing/invalid creds -> 401, valid-but-low -> 403,
    sufficient -> 200, on one representative premium endpoint."""
    path = "analytics/type-distribution"
    assert api.get(path).status_code == 401                                  # no creds
    assert api.get(path, headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert api.get(path, headers=auth_headers(free_token)).status_code == 403
    assert api.get(path, headers=auth_headers(premium_token)).status_code == 200


@pytest.mark.p1
def test_tier_is_read_live(api, make_user):
    """TC-RBAC-08: tier lives in the DB, not the token — checkout and cancel
    take effect on the SAME token without re-login."""
    user = make_user()
    path = "analytics/type-distribution"
    month, year = future_expiry()

    assert api.get(path, headers=user.headers).status_code == 403

    checkout = api.post(
        "billing/checkout",
        headers=user.headers,
        json={"plan_id": "premium",
              "card": {"number": CARDS.visa_ok, "exp_month": month, "exp_year": year, "cvc": "123"}},
    )
    assert checkout.status_code == 200
    assert api.get(path, headers=user.headers).status_code == 200

    api.post("billing/cancel", headers=user.headers)
    assert api.get(path, headers=user.headers).status_code == 403
