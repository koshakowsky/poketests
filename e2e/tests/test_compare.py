"""E2E · Compare page — test-cases/e2e/03-compare.md"""

import pytest
from playwright.sync_api import expect


@pytest.mark.p0
def test_compare_two_renders_table_and_radar(compare_page):
    """E2E-CMP-02: add two pokemon, compare, stat table + radar render."""
    compare_page.open()
    compare_page.add("bulbasaur")
    compare_page.add("charmander")
    expect(compare_page.chips).to_have_count(2)

    compare_page.run()
    expect(compare_page.grid_rows.first).to_be_visible()
    expect(compare_page.radar).to_be_visible()
