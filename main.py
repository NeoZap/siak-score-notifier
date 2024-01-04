import time

from selenium.webdriver.remote.webdriver import WebDriver

from siak.course import SIAKCourseScraper
from siak.portal import SIAKPortal
from siak.constants import SLEEP_DURATION

from utils.discord.webhook import DiscordWebhookSender
from utils.selenium.webdriver import init_webdriver
from utils.logger import log
from utils.storage import JSONFileStorage

from envars import USERNAME, PASSWORD, DISCORD_UID, DISCORD_WEBHOOK, IS_DOCKER_ENV


def run(driver: WebDriver):
    log.info("Running...")

    portal = SIAKPortal(driver=driver, username=USERNAME, password=PASSWORD)
    course_scraper = SIAKCourseScraper(driver)
    json_storage = JSONFileStorage("last.json")

    portal.login()
    while not portal.is_logged_in() or not portal.is_role_student():
        if not portal.is_logged_in():
            log.error("Login failed. Retrying...")
        if not portal.is_role_student():
            log.error("Your role is currently not a student. Retrying...")
        portal.relogin()
    log.success(f"Logged in as {USERNAME}")

    course_detail_links = course_scraper.get_latest_term_course_links()
    course_details = course_scraper.extract_course_details(course_detail_links)

    sender = DiscordWebhookSender(
        data=course_details,
        storage=json_storage,
        discord_webhook=DISCORD_WEBHOOK,
        discord_uid=DISCORD_UID,
    )
    sender.send()

    log.success("Done! Waiting for next request...")

    # Sleep for SLEEP_DURATION seconds (without idling)
    for _ in range(SLEEP_DURATION // 60):
        time.sleep(60)
        driver.current_url


def main():
    driver = init_webdriver(IS_DOCKER_ENV)
    while True:
        try:
            run(driver)
        except Exception as e:
            log.error(f"Exception: {str(e)}. Retrying in 15s...")

            # Restart webdriver
            driver.quit()
            driver = init_webdriver(IS_DOCKER_ENV)

            time.sleep(15)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Aborted by request. Quitting...")
