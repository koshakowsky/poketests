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
