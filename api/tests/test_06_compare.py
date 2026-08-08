"""Compare — test-cases/06-compare.md"""

import pytest

from dataset import PROFILE
from schemas import CompareResponse


@pytest.mark.p0
def test_compare_two_pokemon(premium_api):
    """TC-CMP-01: happy-path comparison of two (shape test).

    The SUT declares stat_comparison/advantages as an untyped dict — our model
    types them fully, i.e. the test pins the contract more strictly than the
    SUT's own OpenAPI schema.
    """
    r = premium_api.post(
        "compare/",
        json={"pokemon_ids": [PROFILE.bulbasaur.id, PROFILE.charmander.id]},
    )
    assert r.status_code == 200
    CompareResponse.model_validate(r.json())
    body = r.json()
    assert [p["name"] for p in body["pokemon"]] == [
        PROFILE.bulbasaur.name, PROFILE.charmander.name,
    ]


@pytest.mark.p0
@pytest.mark.parametrize(
    "ids, expected_status",
    [
        ([], 400),
        ([1], 400),
        ([1, 4], 200),
        ([1, 2, 3, 4, 5, 6], 200),
        ([1, 2, 3, 4, 5, 6, 7], 400),
    ],
    ids=["empty", "one", "min-two", "max-six", "seven"],
)
def test_compare_count_boundaries(premium_api, ids, expected_status):
    """TC-CMP-02: BVA on id count (2..6) — both boundaries and both violations."""
    r = premium_api.post("compare/", json={"pokemon_ids": ids})
    assert r.status_code == expected_status
    if expected_status == 200:
        assert len(r.json()["pokemon"]) == len(ids)


@pytest.mark.p1
def test_compare_stat_comparison_invariants(premium_api):
    """TC-CMP-07: aggregate math invariants on a known pair from the profile.

    Exact values come from the profile anchors, and spread is COMPUTED from
    them — the oracle stays exact but carries no "magic" numbers. The
    invariants (max/min/spread/leader consistent with values) are checked for
    every stat: they are cheap and catch swapped fields better than a single
    pair of numbers.
    """
    weak, strong = PROFILE.bulbasaur, PROFILE.mewtwo
    r = premium_api.post("compare/", json={"pokemon_ids": [weak.id, strong.id]})
    comparison = r.json()["stat_comparison"]
    st = comparison["stat_total"]
    assert st["values"] == {weak.name: weak.stat_total, strong.name: strong.stat_total}
    assert st["leader"] == [strong.name]
    assert st["spread"] == strong.stat_total - weak.stat_total
    for stat, entry in comparison.items():
        values = entry["values"].values()
        assert entry["max"] == max(values), stat
        assert entry["min"] == min(values), stat
        assert entry["spread"] == entry["max"] - entry["min"], stat
