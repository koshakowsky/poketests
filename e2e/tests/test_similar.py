"""E2E · Similar page — test-cases/e2e/05-similar.md"""

import pytest
from playwright.sync_api import expect


@pytest.mark.p0
def test_pick_target_renders_card_table_radar(similar_page):
    """E2E-SIM-01: pick a target → target card + similar grid + radar."""
    similar_page.open()
    similar_page.pick("bulbasaur")
    expect(similar_page.target_card).to_be_visible()
    expect(similar_page.target_card).to_contain_text("bulbasaur")
    expect(similar_page.grid_rows.first).to_be_visible()
    expect(similar_page.radar).to_be_visible()
