"""Analytics - test-cases/07-analytics.md"""

import pytest
from pydantic import TypeAdapter

from dataset import PROFILE
from schemas import CategoryStat, GenerationStats

CATEGORY_LIST = TypeAdapter(list[CategoryStat])
GENERATION_LIST = TypeAdapter(list[GenerationStats])


@pytest.mark.p0
def test_categories_default_grouping(premium_api):
    """TC-ANL-01: default grouping (type) responds and is non-empty (shape test)."""
    r = premium_api.get("analytics/categories")
    assert r.status_code == 200
    rows = r.json()
    CATEGORY_LIST.validate_python(rows)
    assert rows
    for row in rows:
        # min <= avg <= max - an invariant independent of the dataset
        assert row["min_stat_total"] <= row["avg_stat_total"] <= row["max_stat_total"]


@pytest.mark.p1
@pytest.mark.parametrize(
    "group_by",
    ["type", "color", "generation", "habitat", "shape", "growth_rate"],
)
def test_every_valid_group_by(premium_api, group_by):
    """TC-ANL-02: one representative per value of the group_by enum."""
    r = premium_api.get("analytics/categories", params={"group_by": group_by})
    assert r.status_code == 200
    rows = r.json()
    CATEGORY_LIST.validate_python(rows)
    assert rows, f"group_by={group_by} returned no groups"


@pytest.mark.p1
@pytest.mark.parametrize(
    "group_by",
    ["weight", "id", "", "TYPE"],
    ids=["not-a-dimension", "internal-column", "empty", "wrong-case"],
)
def test_invalid_group_by_rejected(premium_api, group_by):
    """TC-ANL-03: outside the enum -> 422 (including a case-mismatch)."""
    r = premium_api.get("analytics/categories", params={"group_by": group_by})
    assert r.status_code == 422


@pytest.mark.p1
def test_category_row_invariants(premium_api):
    """TC-ANL-04: per-row aggregate sanity, independent of the dataset."""
    rows = premium_api.get("analytics/categories", params={"group_by": "type"}).json()
    for row in rows:
        assert row["count"] >= 1, row
        assert row["min_stat_total"] <= row["avg_stat_total"] <= row["max_stat_total"], row
        assert row["category"], "empty category label"


@pytest.mark.p1
def test_type_distribution_percentages(premium_api):
    """TC-ANL-05: percentage is derived from count over the dataset total.

    The sum of counts EXCEEDS the roster size because dual-type pokemon are
    counted under both types - asserted explicitly so the overlap is documented
    as intended rather than looking like a bug.
    """
    rows = premium_api.get("analytics/type-distribution").json()
    assert rows
    for row in rows:
        assert row["count"] >= 1
        assert 0 < row["percentage"] <= 100
        assert row["percentage"] == round(row["count"] / PROFILE.total * 100, 1), row
    counts = [row["count"] for row in rows]
    assert counts == sorted(counts, reverse=True), "not sorted by count desc"
    assert sum(counts) > PROFILE.total, "dual-type pokemon must be double-counted"


@pytest.mark.p0
def test_stat_ranges_structure_and_anchors(api):
    """TC-ANL-06: min <= avg <= max per stat, with exact anchors from the profile.

    Uses the unauthenticated client on purpose: stat-ranges is the one public
    analytics route (it feeds the public search sliders) - see TC-RBAC-01.
    """
    r = api.get("analytics/stat-ranges")
    assert r.status_code == 200
    ranges = r.json()
    for stat in ("hp", "attack", "defense", "sp_attack", "sp_defense", "speed", "stat_total"):
        entry = ranges[stat]
        assert entry["min"] <= entry["avg"] <= entry["max"], stat
    assert ranges["stat_total"]["max"] == PROFILE.stat_total_max
    assert ranges["hp"]["max"] == PROFILE.hp_max


@pytest.mark.p1
def test_generation_stats_exact_counts(premium_api):
    """TC-ANL-07: deterministic oracles from the dataset profile; shape test."""
    r = premium_api.get("analytics/generation-stats")
    assert r.status_code == 200
    gens = r.json()
    GENERATION_LIST.validate_python(gens)
    assert len(gens) == len(PROFILE.generations)
    gen1 = gens[0]
    assert gen1["generation"] == PROFILE.generations[0]
    assert gen1["total_pokemon"] == PROFILE.total
    assert gen1["legendary_count"] == PROFILE.legendary_count
    assert gen1["mythical_count"] == PROFILE.mythical_count
