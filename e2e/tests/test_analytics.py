"""E2E · Analytics page — test-cases/e2e/04-analytics.md"""

import pytest
from playwright.sync_api import expect


@pytest.mark.p0
def test_page_loads_table_and_charts(analytics_page):
    """E2E-ANL-01: table populated and all three charts render."""
    analytics_page.open()
    expect(analytics_page.grid_rows.first).to_be_visible()
    for name in ("avg-total", "by-type", "by-generation"):
        expect(analytics_page.chart(name)).to_be_visible()


@pytest.mark.p1
def test_switching_group_updates_table(analytics_page):
    """E2E-ANL-02: switching the grouping refreshes the table's categories."""
    analytics_page.open()
    expect(analytics_page.first_category()).to_be_visible()
    before = analytics_page.first_category().inner_text()
    analytics_page.group("color")
    # Category values change from type names to colors.
    expect(analytics_page.first_category()).not_to_have_text(before)


@pytest.mark.p2
def test_chart_titles_present(analytics_page, page):
    """E2E-ANL-03: each chart's title is rendered."""
    analytics_page.open()
    for title in ("Average Total Stats", "By type", "Pokemons by generation"):
        expect(page.get_by_role("heading", name=title)).to_be_visible()
