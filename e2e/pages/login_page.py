from playwright.sync_api import Locator

from .base_page import BasePage


class LoginPage(BasePage):
    path = "/login"

    @property
    def email(self) -> Locator:
        return self.page.get_by_test_id("auth-email")

    @property
    def password(self) -> Locator:
        return self.page.get_by_test_id("auth-password")

    @property
    def submit_button(self) -> Locator:
        return self.page.get_by_test_id("auth-submit")

    @property
    def toggle(self) -> Locator:
        return self.page.get_by_test_id("auth-toggle")

    @property
    def error(self) -> Locator:
        return self.page.get_by_test_id("auth-error")

    def login(self, email: str, password: str) -> None:
        self.email.fill(email)
        self.password.fill(password)
        self.submit_button.click()

    def register(self, email: str, password: str) -> None:
        self.toggle.click()  # switch to register mode
        self.email.fill(email)
        self.password.fill(password)
        self.submit_button.click()
