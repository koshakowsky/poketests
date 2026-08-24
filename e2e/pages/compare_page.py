from playwright.sync_api import Locator

from .base_page import BasePage


class ComparePage(BasePage):
    path = "/compare"

    def search(self, name: str) -> None:
        self.page.get_by_test_id("compare-search").fill(name)

    def add(self, name: str) -> None:
        """Type a name and click the matching autocomplete suggestion."""
        self.search(name)
        self.page.get_by_test_id("compare-suggestion").filter(has_text=name).first.click()

    @property
    def suggestions(self) -> Locator:
        return self.page.get_by_test_id("compare-suggestion")

    @property
    def chips(self) -> Locator:
        return self.page.get_by_test_id("compare-chip")

    def remove_first_chip(self) -> None:
        self.page.get_by_test_id("compare-chip-remove").first.click()

    @property
    def run_button(self) -> Locator:
        return self.page.get_by_test_id("compare-run")

    def run(self) -> None:
        self.run_button.click()

    @property
    def grid(self) -> Locator:
        """The grid container. Assertions target this rather than an individual
        row: ag-grid rows are absolutely positioned, transformed and recycled,
        so "is the first row visible" tests the virtualisation internals, not
        the product - and Linux WebKit reports them hidden intermittently.
        """
        return self.page.get_by_test_id("compare-grid")

    @property
    def grid_rows(self) -> Locator:
        return self.page.get_by_test_id("compare-grid").locator(".ag-row")

    @property
    def radar(self) -> Locator:
        return self.page.get_by_test_id("compare-radar").locator("svg.recharts-surface:not([aria-label])")
