"""E2E · Navigation — test-cases/e2e/01-navigation.md"""

import pytest
from playwright.sync_api import expect


@pytest.mark.p0
def test_app_shell_loads(page, base_url):
    """E2E-NAV-01: header + four nav tabs render."""
    page.goto(f"{base_url}/")
    expect(page.get_by_test_id("nav")).to_be_visible()
    for name in ("select", "analytics", "compare", "similar"):
        expect(page.get_by_test_id(f"nav-link-{name}")).to_be_visible()
    expect(page.get_by_role("heading", name="Pokemon select")).to_be_visible()


@pytest.mark.p0
@pytest.mark.parametrize(
    "link, path, heading",
    [
        ("analytics", "/analytics", "Category analysis"),
        ("compare", "/compare", "Compare Pokemon"),
        ("similar", "/similar", "Find a similar Pokemon"),
        ("select", "/", "Pokemon select"),
    ],
    ids=["analytics", "compare", "similar", "select"],
)
def test_nav_routes_to_page(page, base_url, link, path, heading):
    """E2E-NAV-02: each tab client-routes to its page (URL + heading)."""
    page.goto(f"{base_url}/")
    page.get_by_test_id(f"nav-link-{link}").click()
    expect(page).to_have_url(f"{base_url}{path}")
    expect(page.get_by_role("heading", name=heading)).to_be_visible()


@pytest.mark.p1
def test_deeplink_subroute_served_by_spa_fallback(page, base_url):
    """E2E-NAV-04: direct load of /compare works (nginx try_files fallback)."""
    page.goto(f"{base_url}/compare")
    expect(page.get_by_role("heading", name="Compare Pokemon")).to_be_visible()


@pytest.mark.p2
def test_active_tab_highlighted(page, base_url):
    """E2E-NAV-03: the current tab exposes aria-current=page (react-router NavLink)."""
    page.goto(f"{base_url}/compare")
    expect(page.get_by_test_id("nav-link-compare")).to_have_attribute("aria-current", "page")
    expect(page.get_by_test_id("nav-link-select")).not_to_have_attribute("aria-current", "page")


@pytest.mark.p3
def test_no_console_errors_on_load(page, base_url):
    """E2E-NAV-05: no console errors / uncaught exceptions on initial render."""
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"{base_url}/")
    expect(page.get_by_test_id("nav")).to_be_visible()
    assert errors == [], f"console errors on load: {errors}"
