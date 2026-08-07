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


@pytest.mark.p1
def test_filter_by_type(search_page):
    """E2E-SRCH-04: the Type control drives the grid (every row is fire)."""
    search_page.open()
    search_page.select_type("fire")
    expect(search_page.rows.first).to_be_visible()
    # Every rendered row shows a fire badge; charmander is present.
    for row in search_page.rows.all():
        expect(row).to_contain_text("fire")
    expect(search_page.row("charmander")).to_be_visible()


@pytest.mark.p2
def test_generation_with_no_data_is_empty(search_page):
    """E2E-SRCH-05: generation 2 → valid-empty (total 0, no rows, no error)."""
    search_page.open()
    search_page.select_generation("2")
    expect(search_page.total).to_have_text("0")
    expect(search_page.rows).to_have_count(0)
    expect(search_page.error_banner).to_have_count(0)


@pytest.mark.p1
def test_pagination_next_prev(search_page):
    """E2E-SRCH-06: Next/Prev change the range label and the page."""
    search_page.open()
    expect(search_page.page_range).to_have_text("1–50 of 151")
    first_before = search_page.rows.first.inner_text()

    search_page.next_page()
    expect(search_page.page_range).to_have_text("51–100 of 151")
    expect(search_page.rows.first).not_to_have_text(first_before)

    search_page.prev_page()
    expect(search_page.page_range).to_have_text("1–50 of 151")


@pytest.mark.p2
def test_reset_filters(search_page):
    """E2E-SRCH-07: Reset clears filters and restores the full set."""
    search_page.open()
    search_page.filter_by_name("char")
    expect(search_page.total).to_have_text("3")
    search_page.reset()
    expect(search_page.total).to_have_text("151")


@pytest.mark.p2
def test_api_failure_shows_error_banner(search_page, page):
    """E2E-SRCH-08: a failing API surfaces the error banner; the app survives.

    Driven by request interception — unreachable against the real green stack.
    """
    page.route("**/api/pokemon/**", lambda route: route.fulfill(
        status=500, content_type="application/json", body='{"detail": "boom"}'))
    search_page.open()
    expect(search_page.error_banner).to_be_visible()
    expect(search_page.nav).to_be_visible()  # shell still rendered, no crash
