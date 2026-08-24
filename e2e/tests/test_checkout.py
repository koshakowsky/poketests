"""E2E · Checkout & subscription - test-cases/e2e/07-checkout.md"""

import re
from datetime import datetime, timezone

import pytest
from playwright.sync_api import expect

from dataset import CARDS

PREMIUM = re.compile(r"premium", re.I)
FREE = re.compile(r"free", re.I)
FUTURE_YEAR = str(datetime.now(timezone.utc).year + 2)


@pytest.mark.p0
def test_free_user_hits_premium_wall(free_browser, base_url):
    """E2E-PAY-01: a free user sees the upgrade prompt instead of the grid."""
    free_browser.goto(f"{base_url}/analytics")
    expect(free_browser.get_by_test_id("upgrade-prompt")).to_be_visible()
    expect(free_browser.get_by_test_id("view-plans-button")).to_be_visible()
    expect(free_browser.get_by_test_id("analytics-grid")).to_have_count(0)


@pytest.mark.p0
def test_full_upgrade_journey_unlocks_premium(free_browser, checkout_page, account_page, base_url):
    """E2E-PAY-02: pay with a valid card → premium, and the gated page unlocks."""
    checkout_page.open()
    checkout_page.fill_card(CARDS.visa_ok, "12", FUTURE_YEAR, "123")
    checkout_page.pay()

    expect(account_page.page).to_have_url(f"{base_url}/account")
    expect(account_page.account_tier).to_have_text(PREMIUM)

    account_page.page.goto(f"{base_url}/analytics")
    grid = account_page.page.get_by_test_id("analytics-grid")
    expect(grid).to_be_visible()
    expect(grid.locator(".ag-row")).not_to_have_count(0)
    expect(account_page.page.get_by_test_id("upgrade-prompt")).to_have_count(0)


@pytest.mark.p1
def test_declined_card_shows_error(free_browser, checkout_page):
    """E2E-PAY-03: a declined card surfaces an error and grants nothing."""
    checkout_page.open()
    checkout_page.fill_card(CARDS.declined, "12", FUTURE_YEAR, "123")
    checkout_page.pay()
    expect(checkout_page.error).to_be_visible()
    expect(checkout_page.page).to_have_url(re.compile(r"/checkout$"))


@pytest.mark.p1
def test_client_side_validation_blocks_submit(free_browser, checkout_page):
    """E2E-PAY-04: an obviously invalid card is rejected inline, no navigation."""
    checkout_page.open()
    checkout_page.fill_card("1234", "12", FUTURE_YEAR, "123")
    checkout_page.pay()
    expect(checkout_page.field_error("number")).to_be_visible()
    expect(checkout_page.page).to_have_url(re.compile(r"/checkout$"))


@pytest.mark.p1
def test_cancel_relocks_premium(make_premium_user, browser_login, account_page, base_url):
    """E2E-PAY-05: cancelling downgrades to free and re-locks the premium pages."""
    user = make_premium_user()
    browser_login(user.token)
    account_page.open()
    expect(account_page.sub_status).to_have_text(re.compile(r"active", re.I))

    account_page.cancel()
    expect(account_page.sub_status).to_have_text(re.compile(r"canceled", re.I))
    expect(account_page.account_tier).to_have_text(FREE)
    expect(account_page.resubscribe_button).to_be_visible()

    account_page.page.goto(f"{base_url}/analytics")
    expect(account_page.page.get_by_test_id("upgrade-prompt")).to_be_visible()


@pytest.mark.p2
def test_account_shows_masked_card(premium_browser, account_page):
    """E2E-PAY-06: the account shows brand + last4 only, never the full number."""
    account_page.open()
    expect(account_page.sub_details).to_contain_text("visa")
    expect(account_page.sub_details).to_contain_text("4242")
    expect(account_page.sub_details).not_to_contain_text(CARDS.visa_ok)


@pytest.mark.p2
def test_already_premium_on_checkout(premium_browser, checkout_page):
    """E2E-PAY-07: an already-premium user gets no card form on /checkout."""
    checkout_page.open()
    expect(checkout_page.page.get_by_test_id("go-account")).to_be_visible()
    expect(checkout_page.card_number).to_have_count(0)
