from playwright.sync_api import Locator

from .base_page import BasePage


class SearchPage(BasePage):
    path = "/"

    # --- Filters ---
    def filter_by_name(self, text: str) -> None:
        self.page.get_by_test_id("filter-name").fill(text)

    def select_generation(self, value: str) -> None:
        self.page.get_by_test_id("filter-generation").select_option(value)

    def select_type(self, name: str) -> None:
        self.page.get_by_test_id("filter-type").select_option(name)

    def reset(self) -> None:
        self.page.get_by_test_id("reset-filters").click()

    # --- Results ---
    @property
    def total(self) -> Locator:
        return self.page.get_by_test_id("results-total")

    @property
    def rows(self) -> Locator:
        # ag-grid rows scoped inside the grid testid (contains library brittleness).
        return self.page.get_by_test_id("results-grid").locator(".ag-row")

    def row(self, text: str) -> Locator:
        return self.page.get_by_test_id("results-grid").locator(".ag-row", has_text=text)

    @property
    def selected_card(self) -> Locator:
        return self.page.get_by_test_id("selected-card")

    # --- Pagination ---
    @property
    def page_range(self) -> Locator:
        return self.page.get_by_test_id("page-range")

    def next_page(self) -> None:
        self.page.get_by_test_id("page-next").click()

    def prev_page(self) -> None:
        self.page.get_by_test_id("page-prev").click()
