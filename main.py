import json
import time
import datetime
import httpx
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from dotenv import load_dotenv
from typing import Optional
from bs4 import BeautifulSoup, Tag
from webdriver_manager.chrome import ChromeDriverManager


# SIAK URLs
LOGIN_URL = "https://academic.ui.ac.id/main/Authentication/"
HOMEPAGE_URL = "https://academic.ui.ac.id/main/Welcome/"
LOGOUT_URL = "https://academic.ui.ac.id/main/Authentication/Logout"
HISTORY_BY_TERM_URL = "https://academic.ui.ac.id/main/Academic/HistoryByTerm"
ACADEMIC_URL = "https://academic.ui.ac.id/main/Academic/"

# Remote selenium URL (if using docker)
SELENIUM_HUB_URL = "http://selenium_chrome:4444/wd/hub"

# Sleep duration between requests (in seconds)
SLEEP_DURATION = 3600

# Environment variables (includes secrets)
load_dotenv()
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
USERNAME = os.getenv("SIAK_USERNAME")
PASSWORD = os.getenv("SIAK_PASSWORD")
DISCORD_UID = os.getenv("DISCORD_UID")
IS_IN_DOCKER = os.getenv("IS_IN_DOCKER", False)


class SIAKPortal:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.username = USERNAME
        self.password = PASSWORD

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


class SIAKCourseScrapper:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def get_latest_term_course_links(self) -> list[str]:
        self.driver.get(HISTORY_BY_TERM_URL)
        page_source = self.driver.page_source
        latest_term_element = self._get_latest_term_element(page_source)

        if not latest_term_element:
            return []

        course_detail_links = self._extract_course_detail_links(latest_term_element)
        return course_detail_links

    def extract_course_details(self, course_detail_links: list[str]) -> dict[str, dict]:
        data = {}

        for course_detail_link in course_detail_links:
            course_name, score_table = self._get_course_name_and_score_table(
                course_detail_link
            )

            if not score_table:
                data[course_name] = {}
                continue

            data[course_name] = self._extract_course_scores(score_table)

        return data

    def _get_latest_term_element(self, page_source: str) -> Tag:
        soup = BeautifulSoup(page_source, "html.parser")
        return soup.select("td.head.border2")[-1]

    def _extract_course_detail_links(self, latest_term_element: Tag) -> list[str]:
        following_rows = latest_term_element.find_all_next("tr")
        course_detail_links = []

        for row in following_rows:
            detail_links = row.select("td.ce a[href*=ScoreDetail]")

            if detail_links:
                course_detail_links.extend(
                    [ACADEMIC_URL + link["href"] for link in detail_links]
                )

        return course_detail_links

    def _get_course_name_and_score_table(
        self, course_detail_link: str
    ) -> tuple[str, Optional[Tag]]:
        self.driver.get(course_detail_link)
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, "html.parser")

        course_table = soup.find("table", class_="box", style=None)
        course_name = course_table.find_all("tr")[0].find_all("td")[-1].text.strip()

        score_table = soup.find("table", class_="box", style="float:left")
        return course_name, score_table

    def _extract_course_scores(self, score_table: Tag) -> dict[str, dict]:
        data = {}
        score_rows = score_table.select("tr")[1:]
        for row in score_rows:
            details = [elem.text.strip() for elem in row.select("td")]
            component, percentage, score = details[:3]
            data[component] = {"score": score, "percentage": percentage}
        return data


class JSONFileStorage:
    def __init__(self, filename):
        self.filename = filename

    def load(self) -> dict[str, dict]:
        try:
            with open(self.filename, "r") as fd:
                return json.load(fd)
        except FileNotFoundError:
            return {}

    def dump(self, content: dict[str, dict]):
        with open(self.filename, "w") as fd:
            json.dump(content, fd)


class DiscordWebhookSender:
    def __init__(self, data: dict[str, dict], storage: JSONFileStorage):
        self.data = data
        self.storage = storage

    def _build_message(self) -> list[dict[str, str]]:
        fields = []
        for i, (course, scores) in enumerate(self.data.items()):
            field = {"name": "", "value": ""}
            field["name"] += f"{i+1}. {course}:\n"
            if not scores:
                field["value"] += "- No score table found :(\n"
            total_score = 0
            for component, component_info in scores.items():
                if component_info["score"] != "Not published":
                    field[
                        "value"
                    ] += f"- {component}: {component_info['score']} ({component_info['percentage']})\n"
                    total_score += (
                        float(component_info["score"])
                        * float(component_info["percentage"].strip("%"))
                        / 100
                    )
                else:
                    field["value"] += f"- {component}: Not published\n"
            field["value"] += f"- Total Score: **{total_score}**\n"
            fields.append(field)

        return fields

    def send_if_modified(self):
        if self.storage.load() == self.data:
            log.info("No score modification found.")
            return

        fields = self._build_message()
        log.info("Score modification found:")
        for field in fields:
            course, details = field["name"], field["value"]
            print(f"{course}")
            print(f"{details}")

        self.storage.dump(self.data)

        if DISCORD_WEBHOOK:
            httpx.post(
                DISCORD_WEBHOOK,
                json={
                    "content": f"<@{DISCORD_UID}>",
                    "embeds": [
                        {
                            "title": "SIAK Score Update",
                            "description": "New score update!",
                            "fields": fields,
                        }
                    ],
                },
            )
            log.success("Score modification sent!")


class Logger:
    INFO_COLOR = "\033[94m"  # Blue
    ERROR_COLOR = "\033[91m"  # Red
    SUCCESS_COLOR = "\033[92m"  # Green
    RESET_COLOR = "\033[0m"  # Reset color to default
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def info(self, message: str):
        print(
            f"[{self.INFO_COLOR}*{self.RESET_COLOR}] {message} - {datetime.datetime.now()}"
        )

    def error(self, message: str):
        print(
            f"[{self.ERROR_COLOR}!{self.RESET_COLOR}] {message} - {datetime.datetime.now()}"
        )

    def success(self, message: str):
        print(
            f"[{self.SUCCESS_COLOR}+{self.RESET_COLOR}] {message} - {datetime.datetime.now()}"
        )


log = Logger()


def init_webdriver() -> WebDriver:
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--ignore-ssl-errors=yes")
    chrome_options.add_argument("--ignore-certificate-errors")
    if IS_IN_DOCKER:
        return webdriver.Remote(
            command_executor=SELENIUM_HUB_URL, options=chrome_options
        )
    else:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(options=chrome_options, service=service)


def run(driver: WebDriver):
    portal = SIAKPortal(driver)
    scraper = SIAKCourseScrapper(driver)
    storage = JSONFileStorage("last.json")

    portal.login()
    while not portal.is_logged_in() or not portal.is_role_student():
        if not portal.is_logged_in():
            log.error("Login failed. Retrying...")
        if not portal.is_role_student():
            log.error("Your role is currently not a student. Retrying...")
        portal.relogin()
    log.success(f"Logged in as {USERNAME}")

    course_detail_links = scraper.get_latest_term_course_links()
    course_details = scraper.extract_course_details(course_detail_links)

    sender = DiscordWebhookSender(data=course_details, storage=storage)
    sender.send_if_modified()

    log.success("Done! Waiting for next request...")
    time.sleep(SLEEP_DURATION)


def main():
    driver = init_webdriver()
    while True:
        try:
            run(driver)
        except Exception as e:
            log.error(f"Exception: {str(e)}. Retrying...")
            driver.quit()
            driver = init_webdriver()
            time.sleep(15)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Aborted by request. Quitting...")