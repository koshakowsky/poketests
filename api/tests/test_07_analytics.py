"""Analytics — test-cases/07-analytics.md"""

import pytest
from pydantic import TypeAdapter

from dataset import PROFILE
from schemas import CategoryStat, GenerationStats

CATEGORY_LIST = TypeAdapter(list[CategoryStat])
GENERATION_LIST = TypeAdapter(list[GenerationStats])


@pytest.mark.p0
def test_categories_default_grouping(api):
    """TC-ANL-01: default grouping (type) responds and is non-empty (shape test)."""
    r = api.get("analytics/categories")
    assert r.status_code == 200
    rows = r.json()
    CATEGORY_LIST.validate_python(rows)
    assert rows
    for row in rows:
        # min <= avg <= max — an invariant independent of the dataset
        assert row["min_stat_total"] <= row["avg_stat_total"] <= row["max_stat_total"]


@pytest.mark.p1
def test_generation_stats_exact_counts(api):
    """TC-ANL-07: deterministic oracles from the dataset profile; shape test."""
    r = api.get("analytics/generation-stats")
    assert r.status_code == 200
    gens = r.json()
    GENERATION_LIST.validate_python(gens)
    assert len(gens) == len(PROFILE.generations)
    gen1 = gens[0]
    assert gen1["generation"] == PROFILE.generations[0]
    assert gen1["total_pokemon"] == PROFILE.total
    assert gen1["legendary_count"] == PROFILE.legendary_count
    assert gen1["mythical_count"] == PROFILE.mythical_count
