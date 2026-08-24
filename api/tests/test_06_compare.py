"""Compare - test-cases/06-compare.md"""

import pytest

from dataset import PROFILE
from schemas import CompareResponse


@pytest.mark.p0
def test_compare_two_pokemon(premium_api):
    """TC-CMP-01: happy-path comparison of two (shape test).

    The SUT declares stat_comparison/advantages as an untyped dict - our model
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
        PROFILE.bulbasaur.name,
        PROFILE.charmander.name,
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
    """TC-CMP-02: BVA on id count (2..6) - both boundaries and both violations."""
    r = premium_api.post("compare/", json={"pokemon_ids": ids})
    assert r.status_code == expected_status
    if expected_status == 200:
        assert len(r.json()["pokemon"]) == len(ids)


@pytest.mark.p1
@pytest.mark.parametrize(
    "ids, expected_status, expected_len",
    [
        ([1, 1], 400, None),  # collapses to 1 unique -> below the minimum
        ([1, 1, 4], 200, 2),
        ([1, 4, 4, 1], 200, 2),
    ],
    ids=["all-dupes", "dupes-plus-one", "interleaved-dupes"],
)
def test_compare_deduplicates_ids(premium_api, ids, expected_status, expected_len):
    """TC-CMP-03: duplicates collapse before the "at least 2" rule is applied."""
    r = premium_api.post("compare/", json={"pokemon_ids": ids})
    assert r.status_code == expected_status
    if expected_len is not None:
        assert len(r.json()["pokemon"]) == expected_len


@pytest.mark.p1
@pytest.mark.parametrize(
    "ids, expected_status, expected_len",
    [
        ([1, 4, 999999], 200, 2),  # unknown id dropped, 2 valid remain
        ([1, -1], 400, None),  # negative is a valid int with no row -> 1 left
        ([1, 4, -1], 200, 2),
    ],
    ids=["unknown-dropped", "one-valid-left", "negative-dropped"],
)
def test_compare_filters_unknown_ids(premium_api, ids, expected_status, expected_len):
    """TC-CMP-04: unknown ids are silently dropped; the count rule applies to
    what survives, not to what was requested."""
    r = premium_api.post("compare/", json={"pokemon_ids": ids})
    assert r.status_code == expected_status
    if expected_len is not None:
        assert len(r.json()["pokemon"]) == expected_len


@pytest.mark.p1
def test_compare_all_unknown_ids(premium_api):
    """TC-CMP-05: nothing left after filtering -> the service-level 400."""
    r = premium_api.post("compare/", json={"pokemon_ids": [999998, 999999]})
    assert r.status_code == 400
    assert r.json()["detail"] == "Need at least 2 pokemon to compare"


@pytest.mark.p1
@pytest.mark.parametrize(
    "body",
    [{}, {"pokemon_ids": "1,2"}, {"pokemon_ids": [1, "a"]}, {"pokemon_ids": [1.5, 2.5]}],
    ids=["missing-field", "string-not-array", "non-numeric-element", "floats"],
)
def test_compare_invalid_body(premium_api, body):
    """TC-CMP-06: body shape errors are framework validation (422), not business 400."""
    assert premium_api.post("compare/", json=body).status_code == 422


@pytest.mark.p2
def test_compare_advantages_structure(premium_api):
    """TC-CMP-08: each pairing accounts for all six stats and the type verdict
    agrees with its own multiplier."""
    r = premium_api.post(
        "compare/",
        json={"pokemon_ids": [PROFILE.bulbasaur.id, PROFILE.charmander.id]},
    )
    advantages = r.json()["advantages"]
    for name, versus in advantages.items():
        assert name not in versus, "a pokemon must not be compared against itself"
        for opponent, entry in versus.items():
            stat = entry["stat_advantage"]
            assert stat["stats_won"] + stat["stats_lost"] + stat["stats_tied"] == 6, (
                name,
                opponent,
            )
            type_adv = entry["type_advantage"]
            multiplier, verdict = type_adv["best_multiplier"], type_adv["verdict"]
            expected = (
                "super_effective"
                if multiplier > 1
                else "not_effective" if multiplier < 1 else "neutral"
            )
            assert verdict == expected, (name, opponent, multiplier, verdict)


@pytest.mark.p2
def test_compare_preserves_request_order(premium_api):
    """TC-CMP-09: the response echoes the requested order, not the DB order."""
    requested = [4, 1, 7]
    r = premium_api.post("compare/", json={"pokemon_ids": requested})
    assert [p["id"] for p in r.json()["pokemon"]] == requested


@pytest.mark.p1
def test_compare_stat_comparison_invariants(premium_api):
    """TC-CMP-07: aggregate math invariants on a known pair from the profile.

    Values come from the profile anchors and spread is computed from them, so
    the oracle is exact without magic numbers. The invariants run over every
    stat: cheap, and they catch swapped fields that one pair would not.
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
