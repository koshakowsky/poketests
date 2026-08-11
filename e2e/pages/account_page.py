from playwright.sync_api import Locator

from .base_page import BasePage


class AccountPage(BasePage):
    path = "/account"

    @property
    def account_tier(self) -> Locator:
        return self.page.get_by_test_id("account-tier")

    @property
    def sub_details(self) -> Locator:
        return self.page.get_by_test_id("sub-details")

    @property
    def sub_status(self) -> Locator:
        return self.page.get_by_test_id("sub-status")

    @property
    def cancel_button(self) -> Locator:
        return self.page.get_by_test_id("cancel-button")

    @property
    def resubscribe_button(self) -> Locator:
        return self.page.get_by_test_id("resubscribe-button")

    def cancel(self) -> None:
        self.cancel_button.click()
