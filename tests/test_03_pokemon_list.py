"""Pokemon list/search — test-cases/03-pokemon-list-search.md"""

import pytest

from dataset import PROFILE
from schemas import PaginatedResponse


@pytest.mark.p0
def test_default_list(api):
    """TC-LIST-01: default limit/offset/sorting and response shape (shape test)."""
    r = api.get("pokemon/")
    assert r.status_code == 200
    # Validate the shape of the whole response (50 items) once per response
    # type, here; the other list tests check values, not shape.
    PaginatedResponse.model_validate(r.json())
    body = r.json()
    assert body["total"] == PROFILE.total
    assert body["limit"] == 50 and body["offset"] == 0
    assert len(body["items"]) == 50
    assert body["has_more"] is True
    # Default order is stat_total desc. Check both the first item (anchor) and
    # the monotonicity of the whole page: one anchor is not enough — sorting
    # could break in the middle.
    totals = [item["stat_total"] for item in body["items"]]
    assert totals[0] == PROFILE.stat_total_max
    assert totals == sorted(totals, reverse=True)


@pytest.mark.p0
def test_filter_by_single_type(api):
    """TC-LIST-06: types=fire — every item has the fire type."""
    r = api.get("pokemon/", params={"types": "fire", "limit": 100})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "filtering by an existing type must not return an empty set"
    # A "for all" invariant, not "some item": a filter bug usually shows up as
    # foreign records leaking in, not as an empty result.
    for item in items:
        assert "fire" in {t["name"] for t in item["types"]}, item["name"]
    assert any(item["id"] == PROFILE.charmander.id for item in items), \
        f"{PROFILE.charmander.name} must be in the result"


@pytest.mark.p0
@pytest.mark.parametrize("bad_sort", ["__class__", "nonexistent_col", "height_m"])
def test_invalid_sort_by_falls_back_to_id(api, bad_sort):
    """TC-LIST-21: sort_by outside the allowlist -> silent fallback to id, not 500.

    The oracle is "result identical to sort_by=id", not merely status 200:
    otherwise the test would not distinguish a fallback to id from sorting by
    something else. Regression guard: an arbitrary attribute used to crash the
    request with a 500.
    """
    baseline = api.get("pokemon/", params={"sort_by": "id", "sort_order": "asc", "limit": 10})
    r = api.get("pokemon/", params={"sort_by": bad_sort, "sort_order": "asc", "limit": 10})
    assert r.status_code == 200
    assert [i["id"] for i in r.json()["items"]] == [i["id"] for i in baseline.json()["items"]]


@pytest.mark.p0
@pytest.mark.parametrize(
    "limit, expected_status, expected_len",
    [
        (0, 422, None),      # below the bound
        (1, 200, 1),         # lower bound
        (100, 200, 100),     # upper bound
        (101, 422, None),    # above the bound
        (-1, 422, None),     # negative
        ("abc", 422, None),  # non-numeric
    ],
    ids=["zero", "min", "max", "over-max", "negative", "non-numeric"],
)
def test_limit_boundaries(api, limit, expected_status, expected_len):
    """TC-LIST-23: BVA on limit (ge=1, le=100) — the case table 1:1 in parametrize."""
    r = api.get("pokemon/", params={"limit": limit})
    assert r.status_code == expected_status
    if expected_len is not None:
        assert len(r.json()["items"]) == expected_len


@pytest.mark.p1
@pytest.mark.parametrize(
    "min_hp, expected_total",
    [(PROFILE.hp_max, 1), (PROFILE.hp_max + 1, 0)],
    ids=["exact-max-boundary", "beyond-max"],
)
def test_min_hp_boundary_at_chansey(api, min_hp, expected_total):
    """TC-LIST-16 e/f: exact range boundary at the real data maximum.

    The expectation is recomputed from the data, not assumed: the profile's
    hp_max is exactly one record (chansey in gen1), so boundary -> 1,
    boundary+1 -> 0.
    """
    r = api.get("pokemon/", params={"min_hp": min_hp})
    assert r.status_code == 200
    assert r.json()["total"] == expected_total


@pytest.mark.p1
def test_pagination_pages_are_stable(api):
    """TC-LIST-26: three pages by a unique key — no duplicates or gaps.

    Regression guard for the joinedload bug (rows multiplied per each-type,
    and pages came up short).
    """
    ids = []
    for offset in (0, 50, 100):
        r = api.get(
            "pokemon/",
            params={"sort_by": "id", "sort_order": "asc", "limit": 50, "offset": offset},
        )
        page = [item["id"] for item in r.json()["items"]]
        assert len(page) == 50, f"page offset={offset} came up short"
        ids.extend(page)
    assert len(set(ids)) == 150, "duplicates or gaps between pages"


@pytest.mark.p1
@pytest.mark.xfail(
    strict=True,
    reason="BUG-001: LIKE wildcards are not escaped (bugs/BUG-001, case TC-LIST-28); "
    "the test encodes the specification — remove xfail once fixed",
)
@pytest.mark.parametrize("wildcard", ["%", "_"])
def test_name_filter_treats_like_wildcards_literally(api, wildcard):
    """TC-LIST-28: spec — literal search; actual — wildcard injection.

    strict=True: once the bug is fixed the test will start passing, the xfail
    turns into an XPASS error — a signal to remove the marker. Without strict
    the fix would go unnoticed.
    """
    r = api.get("pokemon/", params={"name": wildcard})
    assert r.status_code == 200
    assert r.json()["total"] == 0
