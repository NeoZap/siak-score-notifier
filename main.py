import json
import time
import httpx
import os
import pytz
from datetime import datetime
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
SLEEP_DURATION = 1800

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


class SIAKCourseScraper:
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
    def __init__(self, data: dict, storage: JSONFileStorage):
        self.data = data
        self.storage = storage

    def _build_field(self, course: str, scores: dict) -> dict:
        field = {"name": f"{course}:\n", "value": ""}
        if not scores:
            field["value"] += "- No score table found :(\n"
            return field

        total_score = 0
        for component, component_info in scores.items():
            if component_info["score"] != "Not published":
                score_value = float(component_info["score"])
                percentage_value = float(component_info["percentage"].strip("%")) / 100
                score_contribution = score_value * percentage_value
                field[
                    "value"
                ] += f"- {component}: {component_info['score']} ({component_info['percentage']})\n"
                total_score += score_contribution
            else:
                field["value"] += f"- {component}: Not published\n"

        field["value"] += f"- Total Score: **{total_score}**\n"
        return field

    def _build_message(self) -> list[dict]:
        fields = []
        for i, (course, scores) in enumerate(self.data.items()):
            fields.append(self._build_field(f"{i+1}. {course}", scores))
        return fields

    def _send_webhook(self, content: str, embeds: list[dict]) -> None:
        if DISCORD_WEBHOOK:
            httpx.post(DISCORD_WEBHOOK, json={"content": content, "embeds": embeds})

    def send(self):
        is_modified = self.storage.load() != self.data

        if not is_modified:
            log.info("No score modification found.")
            self._send_webhook(
                "Just a healthcheck",
                [{"title": "SIAK Score Update", "description": "No new changes yet."}],
            )
            log.success("Healthcheck sent!")
        else:
            fields = self._build_message()
            log.info("Score modification found:")
            for field in fields:
                course, details = field["name"], field["value"]
                print(f"{course}")
                print(f"{details}")
            self.storage.dump(self.data)
            self._send_webhook(
                f"<@{DISCORD_UID}>",
                [
                    {
                        "title": "SIAK Score Update",
                        "description": "New score changes!",
                        "fields": fields,
                    }
                ],
            )
            log.success("Score modification sent!")


class TimeZoneLogger:
    INFO_COLOR = "\033[94m"  # Blue
    ERROR_COLOR = "\033[91m"  # Red
    SUCCESS_COLOR = "\033[92m"  # Green
    RESET_COLOR = "\033[0m"  # Reset color to default

    def __init__(self, zone: str, log_file: Optional[str] = None):
        self.timezone = pytz.timezone(zone)
        self.log_file = log_file

    def _get_current_dt(self):
        return datetime.now(self.timezone)

    def _log(self, message: str):
        if self.log_file:
            with open(self.log_file, "a") as fd:
                fd.write(message + "\n")
        print(message)

    def info(self, message: str):
        self._log(
            f"[{self.INFO_COLOR}*{self.RESET_COLOR}] ({self._get_current_dt()}) - {message}"
        )

    def error(self, message: str):
        self._log(
            f"[{self.ERROR_COLOR}!{self.RESET_COLOR}] ({self._get_current_dt()}) - {message}"
        )

    def success(self, message: str):
        self._log(
            f"[{self.SUCCESS_COLOR}+{self.RESET_COLOR}] ({self._get_current_dt()}) - {message}"
        )


log = TimeZoneLogger(zone="Asia/Jakarta", log_file="logs.txt")


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
    log.info("Running...")

    portal = SIAKPortal(driver)
    scraper = SIAKCourseScraper(driver)
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
    sender.send()

    log.success("Done! Waiting for next request...")

    # Sleep for SLEEP_DURATION seconds, while not idling
    for _ in range(SLEEP_DURATION // 60):
        time.sleep(60)
        driver.current_url


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
