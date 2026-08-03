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


@pytest.mark.p1
def test_autocomplete_suggests_matches(compare_page):
    """E2E-CMP-01: typing shows a suggestions dropdown with matches."""
    compare_page.open()
    compare_page.search("bulba")
    suggestion = compare_page.suggestions.filter(has_text="bulbasaur")
    expect(suggestion.first).to_be_visible()


@pytest.mark.p2
def test_compare_button_hidden_below_two(compare_page):
    """E2E-CMP-03: the Compare button appears only once ≥2 are selected."""
    compare_page.open()
    compare_page.add("bulbasaur")
    expect(compare_page.chips).to_have_count(1)
    expect(compare_page.run_button).to_have_count(0)


@pytest.mark.p2
def test_remove_chip(compare_page):
    """E2E-CMP-04: removing a chip drops it from the selection."""
    compare_page.open()
    compare_page.add("bulbasaur")
    compare_page.add("charmander")
    expect(compare_page.chips).to_have_count(2)
    compare_page.remove_first_chip()
    expect(compare_page.chips).to_have_count(1)


@pytest.mark.p3
def test_selection_capped_at_six(compare_page):
    """E2E-CMP-05: the UI blocks a 7th selection (API's 2..6 rule)."""
    compare_page.open()
    for name in ("bulbasaur", "charmander", "squirtle", "pikachu", "jigglypuff", "meowth"):
        compare_page.add(name)
    expect(compare_page.chips).to_have_count(6)
    compare_page.add("eevee")  # 7th — ignored by the UI
    expect(compare_page.chips).to_have_count(6)
