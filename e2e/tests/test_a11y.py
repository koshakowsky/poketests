"""E2E · Accessibility - test-cases/e2e/08-accessibility.md

axe-core audit of the primary user paths. The gate is deliberately asymmetric:
`critical` always fails, `serious` fails only for rules outside the documented
allowlist below. See test-cases/e2e/08-accessibility.md for why.
"""

import pytest
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect

# Pre-existing debt, tracked in bugs/BUG-007-accessibility-violations.md.
# Anything NOT listed here fails the build. Remove an entry once it is fixed.
KNOWN_A11Y_ISSUES = {
    "color-contrast",  # BUG-007: muted greys in the shared palette, app-wide
}

axe = Axe()


def audit(page) -> list[dict]:
    return axe.run(page).response["violations"]


def assert_accessible(page) -> None:
    violations = audit(page)
    critical = [v for v in violations if v["impact"] == "critical"]
    unlisted_serious = [
        v for v in violations if v["impact"] == "serious" and v["id"] not in KNOWN_A11Y_ISSUES
    ]

    def describe(items):
        return "; ".join(f"{v['id']} ({len(v['nodes'])} nodes) - {v['help']}" for v in items)

    assert not critical, f"critical a11y violations: {describe(critical)}"
    assert not unlisted_serious, f"new serious a11y violations: {describe(unlisted_serious)}"


@pytest.mark.p1
def test_search_page_accessible(page, base_url):
    """E2E-A11Y-01: the public search page passes the audit gate."""
    page.goto(f"{base_url}/")
    expect(page.get_by_test_id("results-grid")).to_be_visible()
    assert_accessible(page)


@pytest.mark.p1
def test_login_page_accessible(page, base_url):
    """E2E-A11Y-02: the login form passes the audit gate."""
    page.goto(f"{base_url}/login")
    expect(page.get_by_test_id("login-page")).to_be_visible()
    assert_accessible(page)


@pytest.mark.p2
def test_checkout_page_accessible(free_browser, base_url):
    """E2E-A11Y-03: the payment form passes the audit gate."""
    free_browser.goto(f"{base_url}/checkout")
    expect(free_browser.get_by_test_id("card-number")).to_be_visible()
    assert_accessible(free_browser)


@pytest.mark.p1
@pytest.mark.parametrize(
    "testid, expected_name",
    [
        ("filter-name", "Name"),
        ("filter-type", "Type"),
        ("filter-generation", "Generation"),
        ("filter-group", "Group"),
    ],
)
def test_filter_controls_have_accessible_names(page, base_url, testid, expected_name):
    """E2E-A11Y-04: each filter exposes a real accessible name (BUG-007 guard).

    Named assertion rather than a page scan: a whole-page audit could stay green
    while this specific regression hid inside an allowlisted rule.
    """
    page.goto(f"{base_url}/")
    control = page.get_by_test_id(testid)
    expect(control).to_be_visible()
    # The bound <label>, or aria-label as a fallback; a placeholder does not
    # count. Compared case-insensitively: the captions are uppercased in CSS,
    # which is presentation, not the accessible name.
    name = control.evaluate(
        "el => (el.labels && el.labels.length ? el.labels[0].innerText : el.getAttribute('aria-label')) || ''"
    ).strip()
    assert name, f"{testid} has no accessible name"
    assert name.lower().startswith(expected_name.lower()), f"{testid} announced as {name !r}"


@pytest.mark.p2
def test_login_completable_by_keyboard(page, base_url, make_user):
    """E2E-A11Y-05: the login journey works without a pointing device."""
    user = make_user()
    page.goto(f"{base_url}/login")
    expect(page.get_by_test_id("auth-email")).to_be_visible()

    page.get_by_test_id("auth-email").focus()
    page.keyboard.type(user.email)
    page.keyboard.press("Tab")
    page.keyboard.type(user.password)
    page.keyboard.press("Enter")

    expect(page.get_by_test_id("user-email")).to_have_text(user.email)
