from playwright.sync_api import Locator

from .base_page import BasePage


class ComparePage(BasePage):
    path = "/compare"

    def add(self, name: str) -> None:
        """Type a name and click the matching autocomplete suggestion."""
        self.page.get_by_test_id("compare-search").fill(name)
        self.page.get_by_test_id("compare-suggestion").filter(has_text=name).first.click()

    @property
    def suggestions(self) -> Locator:
        return self.page.get_by_test_id("compare-suggestion")

    @property
    def chips(self) -> Locator:
        return self.page.get_by_test_id("compare-chip")

    @property
    def run_button(self) -> Locator:
        return self.page.get_by_test_id("compare-run")

    def run(self) -> None:
        self.run_button.click()

    @property
    def grid_rows(self) -> Locator:
        return self.page.get_by_test_id("compare-grid").locator(".ag-row")

    @property
    def radar(self) -> Locator:
        return self.page.get_by_test_id("compare-radar").locator("svg.recharts-surface")
