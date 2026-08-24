"""Pokemon list/search - test-cases/03-pokemon-list-search.md"""

import pytest
from allpairspy import AllPairs

from dataset import PROFILE
from schemas import PaginatedResponse
from tools.generate_pairwise import FACTORS, VALUES, is_valid


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
    # the monotonicity of the whole page: one anchor is not enough - sorting
    # could break in the middle.
    totals = [item["stat_total"] for item in body["items"]]
    assert totals[0] == PROFILE.stat_total_max
    assert totals == sorted(totals, reverse=True)


@pytest.mark.p0
def test_filter_by_single_type(api):
    """TC-LIST-06: types=fire - every item has the fire type."""
    r = api.get("pokemon/", params={"types": "fire", "limit": 100})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items, "filtering by an existing type must not return an empty set"
    # A "for all" invariant, not "some item": a filter bug usually shows up as
    # foreign records leaking in, not as an empty result.
    for item in items:
        assert "fire" in {t["name"] for t in item["types"]}, item["name"]
    assert any(
        item["id"] == PROFILE.charmander.id for item in items
    ), f"{PROFILE.charmander.name} must be in the result"


@pytest.mark.p1
def test_search_alias_matches_list(api):
    """TC-LIST-02: /search is an alias of / - same total and same page."""
    params = {"types": "fire", "sort_by": "id", "sort_order": "asc", "limit": 10}
    listing = api.get("pokemon/", params=params).json()
    search = api.get("pokemon/search", params=params).json()
    assert search["total"] == listing["total"]
    assert [i["id"] for i in search["items"]] == [i["id"] for i in listing["items"]]


@pytest.mark.p1
@pytest.mark.parametrize(
    "name, expect_names, expect_total",
    [
        ("char", {"charmander", "charmeleon", "charizard"}, 3),
        ("PIKA", {"pikachu"}, 1),  # case-insensitive
        ("zzzzz", set(), 0),  # valid-empty class
    ],
    ids=["substring", "case-insensitive", "no-match"],
)
def test_name_filter(api, name, expect_names, expect_total):
    """TC-LIST-03, TC-LIST-04, TC-LIST-05: substring match, case-insensitivity, valid-empty."""
    r = api.get("pokemon/", params={"name": name, "limit": 100})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == expect_total
    assert {i["name"] for i in body["items"]} == expect_names
    if expect_total == 0:
        assert body["has_more"] is False


@pytest.mark.p1
def test_types_and_semantics(api):
    """TC-LIST-07: a multi-type filter is AND, not OR."""
    r = api.get("pokemon/", params={"types": "grass,poison", "limit": 100})
    items = r.json()["items"]
    assert items
    for item in items:
        names = {t["name"] for t in item["types"]}
        assert {"grass", "poison"} <= names, item["name"]
    assert any(i["id"] == PROFILE.bulbasaur.id for i in items)
    # OR semantics would return a non-empty set here; AND must not.
    assert api.get("pokemon/", params={"types": "fire,water"}).json()["total"] == 0


@pytest.mark.p2
def test_unknown_type_is_valid_empty(api):
    """TC-LIST-08: a value outside the type domain is a valid empty result, not 422."""
    r = api.get("pokemon/", params={"types": "plasma"})
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.p1
@pytest.mark.parametrize(
    "generation, expected_total",
    [(1, PROFILE.total), (2, 0)],
    ids=["seeded-gen", "valid-empty-gen"],
)
def test_generation_filter(api, generation, expected_total):
    """TC-LIST-09, TC-LIST-10: only Gen I is seeded, so Gen II is the valid-empty class."""
    r = api.get("pokemon/", params={"generation": generation})
    assert r.status_code == 200
    assert r.json()["total"] == expected_total


@pytest.mark.p2
@pytest.mark.parametrize(
    "params",
    [{"generation": "abc"}, {"is_legendary": "maybe"}],
    ids=["generation-non-numeric", "is_legendary-non-bool"],
)
def test_type_coercion_errors(api, params):
    """TC-LIST-11, TC-LIST-15: values that cannot coerce to the declared type -> 422."""
    assert api.get("pokemon/", params=params).status_code == 422


@pytest.mark.p1
def test_legendary_and_mythical_flags(api):
    """TC-LIST-12, TC-LIST-13, TC-LIST-14: legendary and mythical are independent flags.

    mew is mythical but NOT legendary, so it must appear in the is_legendary=false
    set - the classic off-by-one-concept bug this pins down.
    """
    legendary = api.get("pokemon/", params={"is_legendary": "true", "limit": 100}).json()
    assert legendary["total"] == PROFILE.legendary_count
    assert all(i["is_legendary"] for i in legendary["items"])
    assert PROFILE.mew.id not in {i["id"] for i in legendary["items"]}

    mythical = api.get("pokemon/", params={"is_mythical": "true", "limit": 100}).json()
    assert mythical["total"] == PROFILE.mythical_count
    assert {i["id"] for i in mythical["items"]} == {PROFILE.mew.id}

    not_legendary = api.get("pokemon/", params={"is_legendary": "false", "limit": 100}).json()
    assert not_legendary["total"] == PROFILE.total - PROFILE.legendary_count
    ids = {i["id"] for i in not_legendary["items"]}
    assert PROFILE.mewtwo.id not in ids
    assert PROFILE.mew.id in ids


@pytest.mark.p2
def test_contradictory_range_is_empty_not_error(api):
    """TC-LIST-17: min>max is an unsatisfiable filter, not a validation error."""
    r = api.get("pokemon/", params={"min_stat_total": 600, "max_stat_total": 300})
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.p2
def test_color_filter_cross_checked_via_detail(api):
    """TC-LIST-18: `color` is filterable but absent from the list schema.

    The list body cannot confirm it, so the oracle goes through the detail
    endpoint - otherwise the filter would be untestable at this layer.
    """
    r = api.get("pokemon/", params={"color": "red", "limit": 100})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items
    detail = api.get(f"pokemon/{items[0]['id']}").json()
    assert detail["color"] == "red"


@pytest.mark.p1
@pytest.mark.parametrize(
    "sort_by, sort_order",
    [("stat_total", "desc"), ("id", "asc")],
    ids=["stat_total-desc", "id-asc"],
)
def test_sorting(api, sort_by, sort_order):
    """TC-LIST-19, TC-LIST-20: the requested sort key and direction are honored."""
    r = api.get("pokemon/", params={"sort_by": sort_by, "sort_order": sort_order, "limit": 100})
    values = [i[sort_by] for i in r.json()["items"]]
    assert values == sorted(values, reverse=sort_order == "desc")


@pytest.mark.p1
@pytest.mark.parametrize(
    "sort_order, expected",
    [("asc", 200), ("desc", 200), ("up", 422), ("ASC", 422)],
    ids=["asc", "desc", "not-in-pattern", "wrong-case"],
)
def test_sort_order_pattern(api, sort_order, expected):
    """TC-LIST-22: sort_order is pattern-validated (case-sensitive), unlike sort_by."""
    assert api.get("pokemon/", params={"sort_order": sort_order}).status_code == expected


@pytest.mark.p1
@pytest.mark.parametrize(
    "offset, limit, expected_len, expected_has_more",
    [
        (0, 50, 50, True),
        (PROFILE.total - 1, 50, 1, False),  # partial last page
        (1000, 50, 0, False),  # past the end
    ],
    ids=["first-page", "partial-last-page", "past-the-end"],
)
def test_offset_boundaries(api, offset, limit, expected_len, expected_has_more):
    """TC-LIST-24: offset boundaries - past-the-end is empty but still 200."""
    r = api.get("pokemon/", params={"offset": offset, "limit": limit})
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == expected_len
    assert body["total"] == PROFILE.total
    assert body["has_more"] is expected_has_more


@pytest.mark.p1
def test_negative_offset_rejected(api):
    """TC-LIST-24: offset has ge=0."""
    assert api.get("pokemon/", params={"offset": -1}).status_code == 422


@pytest.mark.p1
@pytest.mark.parametrize(
    "offset, limit",
    [(0, 100), (100, 50), (PROFILE.total - 50, 50)],
    ids=["more-remain", "one-left", "exact-boundary"],
)
def test_has_more_matches_the_formula(api, offset, limit):
    """TC-LIST-25: has_more == (offset + limit) < total, checked at the boundary.

    Computed from the response's own total rather than a literal, so the case
    stays correct if the dataset profile changes.
    """
    body = api.get("pokemon/", params={"offset": offset, "limit": limit}).json()
    assert body["has_more"] is ((offset + limit) < body["total"])


@pytest.mark.p2
@pytest.mark.parametrize(
    "types, expect_filtered",
    [("", False), (",,", False), (" grass , poison ", True)],
    ids=["empty", "separators-only", "whitespace-padded"],
)
def test_types_csv_parsing(api, types, expect_filtered):
    """TC-LIST-30: CSV parsing trims and drops empties before filtering."""
    body = api.get("pokemon/", params={"types": types, "limit": 100}).json()
    if expect_filtered:
        # Equivalent to the unpadded query, not merely "some result".
        canonical = api.get("pokemon/", params={"types": "grass,poison", "limit": 100}).json()
        assert body["total"] == canonical["total"]
        assert [i["id"] for i in body["items"]] == [i["id"] for i in canonical["items"]]
    else:
        assert body["total"] == PROFILE.total, "an empty list must not filter anything"


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
        (0, 422, None),  # below the bound
        (1, 200, 1),  # lower bound
        (100, 200, 100),  # upper bound
        (101, 422, None),  # above the bound
        (-1, 422, None),  # negative
        ("abc", 422, None),  # non-numeric
    ],
    ids=["zero", "min", "max", "over-max", "negative", "non-numeric"],
)
def test_limit_boundaries(api, limit, expected_status, expected_len):
    """TC-LIST-23: BVA on limit (ge=1, le=100) - the case table 1:1 in parametrize."""
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
    """TC-LIST-26: three pages by a unique key - no duplicates or gaps.

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
@pytest.mark.parametrize("wildcard", ["%", "_"])
def test_name_filter_treats_like_wildcards_literally(api, wildcard):
    """TC-LIST-28: `name` filter matches LIKE wildcards literally.

    Regression guard for BUG-001 (bugs/BUG-001): `%`/`_` used to leak into the
    ILIKE pattern and return everything; now they are escaped, so a name with
    no literal `%`/`_` matches nothing. Was xfail(strict) until the SUT fix.
    """
    r = api.get("pokemon/", params={"name": wildcard})
    assert r.status_code == 200
    assert r.json()["total"] == 0


@pytest.mark.p2
def test_pagination_stable_with_non_unique_sort_key(api):
    """TC-LIST-29: pagination is deterministic even on a non-unique sort key.

    Regression guard for BUG-002 (bugs/BUG-002): `stat_total` has many ties;
    without a secondary id tiebreaker the order inside a tie group was
    undefined and pages could duplicate/drop rows. Now `ORDER BY <key>, id`.
    """

    def collect(offset):
        r = api.get(
            "pokemon/",
            params={"sort_by": "stat_total", "sort_order": "desc", "limit": 50, "offset": offset},
        )
        return [item["id"] for item in r.json()["items"]]

    ids = collect(0) + collect(50) + collect(100)
    assert len(ids) == 150
    assert len(set(ids)) == 150, "duplicates or gaps between pages on a tied key"
    # Deterministic across identical requests (stable tie order).
    assert collect(0) == ids[:50]

    # TC-LIST-27: pairwise
    # The combinations come from the same generator that produced the table in the
    # catalog (tools/generate_pairwise.py), so the documented set and the executed
    # set cannot drift apart.


PAIRWISE_ROWS = [dict(zip(FACTORS, row)) for row in AllPairs(VALUES, filter_func=is_valid)]


def _pairwise_id(row: dict) -> str:
    parts = [
        f"{k}={row[k]}" for k in ("types", "generation", "is_legendary") if row[k] is not None
    ]
    return (
        "-".join(parts or ["nofilter"]) + f"-{row['sort_by']}-{row['sort_order']}-{row['limit']}"
    )


def _params(row: dict) -> dict:
    return {k: v for k, v in row.items() if v is not None}


@pytest.mark.p2
@pytest.mark.parametrize("row", PAIRWISE_ROWS, ids=_pairwise_id)
def test_pairwise_filter_combinations(api, row):
    """TC-LIST-27: all-pairs coverage of the filter/sort/limit factors.

    Pairwise buys combination coverage, so the oracle is the invariants that
    hold for every row, not a per-row hardcoded total. Combinations come from
    tools/generate_pairwise.py, the same generator that produced the catalog
    table.
    """
    r = api.get("pokemon/", params=_params(row))
    assert r.status_code == 200, r.text
    body = r.json()
    items = body["items"]

    assert len(items) <= row["limit"]

    for item in items:
        if row["types"] is not None:
            assert row["types"] in {t["name"] for t in item["types"]}, item["name"]
        if row["generation"] is not None:
            assert item["generation"] == row["generation"], item["name"]
        if row["is_legendary"] is not None:
            assert item["is_legendary"] is row["is_legendary"], item["name"]

            # Ordering. With limit=1 monotonicity is unobservable, so compare against a
            # wide page of the same query: the single item must be its extremum.
    wide = api.get("pokemon/", params={**_params(row), "limit": 100}).json()
    assert wide["total"] == body["total"], "total must not depend on page size"

    key = row["sort_by"]
    values = [item[key] for item in wide["items"]]
    assert values == sorted(values, reverse=row["sort_order"] == "desc"), "wrong order"
    if items:
        assert items[0][key] == values[0], "first item is not the extremum of the filtered set"
