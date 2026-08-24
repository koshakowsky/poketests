from playwright.sync_api import Locator

from .base_page import BasePage


class AnalyticsPage(BasePage):
    path = "/analytics"

    @property
    def grid(self) -> Locator:
        """The grid container. Assertions target this rather than an individual
        row: ag-grid rows are absolutely positioned, transformed and recycled,
        so "is the first row visible" tests the virtualisation internals, not
        the product - and Linux WebKit reports them hidden intermittently.
        """
        return self.page.get_by_test_id("analytics-grid")

    @property
    def grid_rows(self) -> Locator:
        return self.page.get_by_test_id("analytics-grid").locator(".ag-row")

    def first_category(self) -> Locator:
        return self.grid_rows.first.locator(".ag-cell").first

    def group(self, value: str) -> None:
        self.page.get_by_test_id(f"group-{value}").click()

    def chart(self, name: str) -> Locator:
        """name ∈ {avg-total, by-type, by-generation}."""
        # :not([aria-label]) excludes recharts legend-icon surfaces (they carry
        # an aria-label); only the main chart surface remains.
        return self.page.get_by_test_id(f"chart-{name}").locator("svg.recharts-surface:not([aria-label])")
