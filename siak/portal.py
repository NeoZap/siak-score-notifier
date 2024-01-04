from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from .constants import LOGIN_URL, LOGOUT_URL, HOMEPAGE_URL


class SIAKPortal:
    def __init__(self, driver: WebDriver, username: str, password: str):
        self.driver = driver
        self.username = username
        self.password = password

    def login(self):
        self.driver.get(LOGIN_URL)
        self.driver.execute_script(
            f"arguments[0].value = '{self.username}';",
            self.driver.find_element(By.ID, "u"),
        )
        self.driver.execute_script(
            f"arguments[0].value = '{self.password}';",
            self.driver.find_element(By.NAME, "p"),
        )
        self.driver.execute_script(
            "arguments[0].click();",
            self.driver.find_element(By.XPATH, "//input[@value='Login']"),
        )

    def relogin(self):
        self.driver.get(LOGOUT_URL)
        self.login()

    def is_logged_in(self) -> bool:
        return HOMEPAGE_URL in self.driver.current_url

    def is_role_student(self) -> bool:
        return "Mahasiswa" in self.driver.page_source
