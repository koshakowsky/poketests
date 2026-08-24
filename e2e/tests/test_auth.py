"""E2E · Authentication - test-cases/e2e/06-auth.md"""

import re
import uuid

import pytest
from playwright.sync_api import expect

FREE = re.compile(r"free", re.I)


def _unique_email() -> str:
    return f"e2e+{uuid.uuid4().hex}@test.io"


@pytest.mark.p0
def test_register_new_account(login_page):
    """E2E-AUTH-01: register from the UI lands logged in on the free tier."""
    login_page.open()
    login_page.register(_unique_email(), "password123")
    expect(login_page.user_email).to_be_visible()
    expect(login_page.user_tier).to_have_text(FREE)
    expect(login_page.login_link).to_have_count(0)


@pytest.mark.p0
def test_login_existing_account(login_page, make_user):
    """E2E-AUTH-02: log in with an account created via the API."""
    user = make_user()
    login_page.open()
    login_page.login(user.email, user.password)
    expect(login_page.user_email).to_have_text(user.email)
    expect(login_page.logout_button).to_be_visible()


@pytest.mark.p0
def test_anonymous_premium_redirects_to_login(page, base_url):
    """E2E-AUTH-03: an anonymous visit to a premium page redirects to /login."""
    page.goto(f"{base_url}/analytics")
    expect(page).to_have_url(re.compile(r"/login$"))
    expect(page.get_by_test_id("login-page")).to_be_visible()


@pytest.mark.p1
def test_invalid_login_shows_error(login_page, make_user):
    """E2E-AUTH-04: wrong password surfaces an error and creates no session."""
    user = make_user()
    login_page.open()
    login_page.login(user.email, "wrong-password")
    expect(login_page.error).to_be_visible()
    expect(login_page.login_link).to_be_visible()  # still anonymous


@pytest.mark.p1
def test_logout_clears_session(login_page, make_user, base_url, page):
    """E2E-AUTH-05: logging out returns to the anonymous state and re-locks premium."""
    user = make_user()
    login_page.open()
    login_page.login(user.email, user.password)
    expect(login_page.user_email).to_be_visible()
    login_page.logout()
    expect(login_page.login_link).to_be_visible()
    page.goto(f"{base_url}/analytics")
    expect(page).to_have_url(re.compile(r"/login$"))


@pytest.mark.p1
def test_post_login_returns_to_intended_page(page, base_url, login_page, make_user):
    """E2E-AUTH-06: after login the guard returns the user to the intended page."""
    user = make_user()
    page.goto(f"{base_url}/compare")               # anonymous → redirected to login
    expect(page).to_have_url(re.compile(r"/login$"))
    login_page.login(user.email, user.password)
    expect(page).to_have_url(f"{base_url}/compare")


@pytest.mark.p1
def test_session_persists_across_reload(login_page, browser_login, make_user, page):
    """E2E-AUTH-07: the session survives a reload (token restored from storage)."""
    user = make_user()
    browser_login(user.token)
    login_page.open()
    expect(login_page.user_email).to_be_visible()
    page.reload()
    expect(login_page.user_email).to_be_visible()


@pytest.mark.p2
def test_toggle_login_register(login_page, page):
    """E2E-AUTH-08: toggling switches the form between login and register."""
    login_page.open()
    expect(page.get_by_role("heading", name="Welcome back")).to_be_visible()
    login_page.toggle.click()
    expect(page.get_by_role("heading", name="Create account")).to_be_visible()
