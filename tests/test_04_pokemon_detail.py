"""Pokemon detail — test-cases/04-pokemon-detail.md"""

import pytest

from dataset import PROFILE
from schemas import PokemonDetail

@pytest.mark.p0
def test_detail_of_existing_pokemon(api):
    """TC-DET-01: bulbasaur card — id, name, stats, both types (shape test)."""
    anchor = PROFILE.bulbasaur
    r = api.get(f"pokemon/{anchor.id}")
    assert r.status_code == 200
    PokemonDetail.model_validate(r.json())
    body = r.json()
    assert body["id"] == anchor.id
    assert body["name"] == anchor.name
    assert body["stat_total"] == anchor.stat_total
    assert {t["name"] for t in body["types"]} == anchor.types


@pytest.mark.p0
def test_detail_not_found(api):
    """TC-DET-04: unknown id -> 404 with a clear detail."""
    r = api.get("pokemon/999999")
    assert r.status_code == 404
    assert r.json()["detail"] == "Pokemon not found"


@pytest.mark.p1
@pytest.mark.parametrize(
    "pokemon_id, expected_status",
    [
        (PROFILE.max_id, 200),      # highest seeded record
        (PROFILE.max_id + 1, 404),  # just past the set
        (0, 404),
        (-1, 404),
        ("abc", 422),
        (1.5, 422),
    ],
    ids=["last-seeded", "just-beyond", "zero", "negative", "string", "float"],
)
def test_detail_id_boundaries(api, pokemon_id, expected_status):
    """TC-DET-05: path-parameter boundaries.

    The 404/422 distinction matters: -1 is a valid int that does not exist
    (404), while "abc" fails type parsing (422). Merging these classes into a
    single "negative" case would hide a validation regression.
    """
    assert api.get(f"pokemon/{pokemon_id}").status_code == expected_status
