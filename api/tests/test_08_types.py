"""Types - test-cases/08-types.md"""

import pytest
from pydantic import TypeAdapter

from schemas import EffectivenessResponse, TypeRef

TYPE_LIST = TypeAdapter(list[TypeRef])


@pytest.mark.p0
def test_types_list(api):
    """TC-TYP-01: type list, known names are present (shape test)."""
    r = api.get("types/")
    assert r.status_code == 200
    TYPE_LIST.validate_python(r.json())
    names = {t["name"] for t in r.json()}
    assert {"fire", "water", "grass", "electric"} <= names


@pytest.mark.p0
def test_type_effectiveness_for_fire(api):
    """TC-TYP-03 + TC-TYP-06: structure and domain multipliers for fire (shape test).

    The type id is taken from the API, not hardcoded: type numbering is a
    PokeAPI detail we make no contract about.
    """
    types = {t["name"]: t["id"] for t in api.get("types/").json()}
    r = api.get(f"types/{types['fire']}/effectiveness")
    assert r.status_code == 200
    EffectivenessResponse.model_validate(r.json())
    body = r.json()
    attacking = {row["type"]: row["multiplier"] for row in body["attacking"]}
    assert attacking.get("grass") == 2.0, "fire should be strong against grass"
    assert attacking.get("water") == 0.5, "fire should be weak against water"


@pytest.mark.p2
def test_types_sorted_by_name(api):
    """TC-TYP-02: the list is alphabetically ordered."""
    names = [t["name"] for t in api.get("types/").json()]
    assert names == sorted(names)


@pytest.mark.p1
def test_effectiveness_multipliers_are_in_domain(api):
    """TC-TYP-06: only non-neutral multipliers are stored, so every value must
    be one of the three meaningful ones - a stored 1.0 would mean dead rows."""
    types = {t["name"]: t["id"] for t in api.get("types/").json()}
    body = api.get(f"types/{types['fire']}/effectiveness").json()
    for direction in ("attacking", "defending"):
        for row in body[direction]:
            assert row["multiplier"] in {0.0, 0.5, 2.0}, (direction, row)


@pytest.mark.p0
def test_type_effectiveness_not_found(api):
    """TC-TYP-04: unknown type -> 404 (regression guard: used to be 500/N+1)."""
    r = api.get("types/999999/effectiveness")
    assert r.status_code == 404


@pytest.mark.p2
@pytest.mark.parametrize("type_id", ["abc", "1.5"], ids=["non-numeric", "float"])
def test_effectiveness_malformed_id(api, type_id):
    """TC-TYP-05: a path param that cannot coerce to int -> 422, not 404."""
    assert api.get(f"types/{type_id}/effectiveness").status_code == 422
