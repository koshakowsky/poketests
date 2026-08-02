"""E2E · Select page — test-cases/e2e/02-search.md"""

import pytest
from playwright.sync_api import expect


@pytest.mark.p0
def test_default_results_load(search_page):
    """E2E-SRCH-01: default grid loads, total 151, first row is mewtwo (sort desc).

    We don't assert the row *count* — ag-grid virtualizes, so only visible rows
    are in the DOM. We assert the counter and the top row instead.
    """
    search_page.open()
    expect(search_page.total).to_have_text("151")
    expect(search_page.rows.first).to_contain_text("mewtwo")


@pytest.mark.p0
def test_filter_by_name_narrows_grid(search_page):
    """E2E-SRCH-02: name filter narrows results.

    The input debounces ~350 ms; `to_have_text`/`to_have_count` auto-retry
    until the debounced fetch lands — no sleep.
    """
    search_page.open()
    search_page.filter_by_name("char")
    expect(search_page.total).to_have_text("3")
    expect(search_page.rows).to_have_count(3)  # 3 rows fit the viewport, no virtualization


@pytest.mark.p0
def test_row_click_opens_detail_card(search_page):
    """E2E-SRCH-03: clicking a row opens the detail card with stats."""
    search_page.open()
    search_page.filter_by_name("bulbasaur")
    expect(search_page.total).to_have_text("1")
    search_page.row("bulbasaur").click()
    card = search_page.selected_card
    expect(card).to_be_visible()
    expect(card).to_contain_text("bulbasaur")
    expect(card).to_contain_text("Total 318")
