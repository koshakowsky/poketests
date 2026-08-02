"""Page Object base — header nav is present on every page.

POM keeps selectors out of tests: tests speak in intent (`add`, `filter_by_name`),
locators live here. Selection order follows the catalog: data-testid first, then
role/text, then library DOM (ag-grid `.ag-row`, recharts `svg`) scoped inside a
testid container.
"""

from playwright.sync_api import Locator, Page


class BasePage:
    path = "/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self):
        # Explicit absolute navigation — POM does not rely on context base_url.
        self.page.goto(f"{self.base_url}{self.path}")
        return self

    # --- Header / nav (shared shell) ---
    @property
    def nav(self) -> Locator:
        return self.page.get_by_test_id("nav")

    def nav_link(self, name: str) -> Locator:
        return self.page.get_by_test_id(f"nav-link-{name}")

    def nav_to(self, name: str) -> None:
        self.nav_link(name).click()
