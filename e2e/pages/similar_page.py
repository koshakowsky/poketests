from playwright.sync_api import Locator

from .base_page import BasePage


class SimilarPage(BasePage):
    path = "/similar"

    def pick(self, name: str) -> None:
        self.page.get_by_test_id("similar-search").fill(name)
        self.page.get_by_test_id("similar-suggestion").filter(has_text=name).first.click()

    @property
    def target_card(self) -> Locator:
        return self.page.get_by_test_id("target-card")

    @property
    def grid(self) -> Locator:
        """The grid container. Assertions target this rather than an individual
        row: ag-grid rows are absolutely positioned, transformed and recycled,
        so "is the first row visible" tests the virtualisation internals, not
        the product - and Linux WebKit reports them hidden intermittently.
        """
        return self.page.get_by_test_id("similar-grid")

    @property
    def grid_rows(self) -> Locator:
        return self.page.get_by_test_id("similar-grid").locator(".ag-row")

    @property
    def radar(self) -> Locator:
        return self.page.get_by_test_id("similar-radar").locator("svg.recharts-surface:not([aria-label])")
