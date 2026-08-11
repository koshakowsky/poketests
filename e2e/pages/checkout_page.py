from playwright.sync_api import Locator

from .base_page import BasePage


class CheckoutPage(BasePage):
    path = "/checkout"

    @property
    def plan_price(self) -> Locator:
        return self.page.get_by_test_id("plan-price")

    @property
    def card_number(self) -> Locator:
        return self.page.get_by_test_id("card-number")

    @property
    def exp_month(self) -> Locator:
        return self.page.get_by_test_id("exp-month")

    @property
    def exp_year(self) -> Locator:
        return self.page.get_by_test_id("exp-year")

    @property
    def cvc(self) -> Locator:
        return self.page.get_by_test_id("cvc")

    @property
    def pay_button(self) -> Locator:
        return self.page.get_by_test_id("pay-button")

    @property
    def error(self) -> Locator:
        return self.page.get_by_test_id("checkout-error")

    def field_error(self, field: str) -> Locator:
        """field ∈ {number, expiry, cvc}."""
        return self.page.get_by_test_id(f"error-{field}")

    def fill_card(self, number: str, month: str, year: str, cvc: str) -> None:
        self.card_number.fill(number)
        self.exp_month.fill(month)
        self.exp_year.fill(year)
        self.cvc.fill(cvc)

    def pay(self) -> None:
        self.pay_button.click()
