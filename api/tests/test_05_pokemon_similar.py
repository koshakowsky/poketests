"""Pokemon similar — test-cases/05-pokemon-similar.md"""

import pytest
from pydantic import TypeAdapter

from schemas import SimilarEntry

# TypeAdapter — the pydantic tool for validating "bare" containers
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


@pytest.mark.p0
def test_similar_not_found(premium_api):
    """TC-SIM-05: unknown pokemon -> 404 (after premium auth passes)."""
    r = premium_api.get("pokemon/999999/similar")
    assert r.status_code == 404
