"""Pokemon similar - test-cases/05-pokemon-similar.md"""

import pytest
from pydantic import TypeAdapter

from dataset import PROFILE
from schemas import SimilarEntry

# TypeAdapter - the pydantic tool for validating "bare" containers
# (list[Model]): this endpoint's response root is an array, not an object.
SIMILAR_LIST = TypeAdapter(list[SimilarEntry])


@pytest.mark.p0
def test_similar_for_existing_pokemon(premium_api):
    """TC-SIM-01: default limit=10, item shape, sorted by score (shape test)."""
    r = premium_api.get("pokemon/1/similar")
    assert r.status_code == 200
    items = r.json()
    SIMILAR_LIST.validate_python(items)
    assert len(items) == 10
    scores = [e["similarity_score"] for e in items]
    assert scores == sorted(scores, reverse=True)
    # The pokemon must not be recommended to itself (TC-SIM-03, cheap to check here)
    assert all(e["pokemon"]["id"] != 1 for e in items)


@pytest.mark.p1
@pytest.mark.parametrize(
    "limit, expected_status, expected_len",
    [(0, 422, None), (1, 200, 1), (50, 200, 50), (51, 422, None), (-1, 422, None)],
    ids=["zero", "min", "max", "over-max", "negative"],
)
def test_similar_limit_boundaries(premium_api, limit, expected_status, expected_len):
    """TC-SIM-04: BVA on limit (ge=1, le=50)."""
    r = premium_api.get(f"pokemon/{PROFILE.bulbasaur.id}/similar", params={"limit": limit})
    assert r.status_code == expected_status
    if expected_len is not None:
        assert len(r.json()) == expected_len


@pytest.mark.p1
def test_similar_score_invariants(premium_api):
    """TC-SIM-02, TC-SIM-06: score is a bounded, non-increasing similarity and
    matching_types can only contain the target's own types."""
    r = premium_api.get(f"pokemon/{PROFILE.bulbasaur.id}/similar", params={"limit": 20})
    entries = r.json()
    scores = [e["similarity_score"] for e in entries]
    assert scores == sorted(scores, reverse=True)
    for entry in entries:
        assert 0 <= entry["similarity_score"] <= 100, entry
        assert entry["stat_difference"] >= 0, entry
        assert set(entry["matching_types"]) <= PROFILE.bulbasaur.types, entry


@pytest.mark.p2
def test_similar_ranks_close_relatives_first(premium_api):
    """TC-SIM-07: domain plausibility - the metric is not just numerically sane
    but actually surfaces the evolution line. A soft oracle: ivysaur (the direct
    evolution of bulbasaur) must land in the top 5."""
    entries = premium_api.get(
        f"pokemon/{PROFILE.bulbasaur.id}/similar", params={"limit": 5}
    ).json()
    assert "ivysaur" in {e["pokemon"]["name"] for e in entries}


@pytest.mark.p0
def test_similar_not_found(premium_api):
    """TC-SIM-05: unknown pokemon -> 404 (after premium auth passes)."""
    r = premium_api.get("pokemon/999999/similar")
    assert r.status_code == 404
