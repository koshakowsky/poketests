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


@pytest.mark.p2
def test_similar_top_is_close_relative(similar_page):
    """E2E-SIM-02: the UI presents the highest match first (a close relative).

    Ordering correctness is API-tested; here we confirm the UI shows it in
    order — bulbasaur's top match is its evolution, ivysaur.
    """
    similar_page.open()
    similar_page.pick("bulbasaur")
    expect(similar_page.grid_rows.first).to_contain_text("ivysaur")


@pytest.mark.p2
def test_target_card_shows_meta(similar_page):
    """E2E-SIM-03: the target card carries detail meta (generation, etc.)."""
    similar_page.open()
    similar_page.pick("bulbasaur")
    expect(similar_page.target_card).to_contain_text("Gen 1")
