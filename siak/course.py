from selenium.webdriver.remote.webdriver import WebDriver
from typing import Optional
from bs4 import BeautifulSoup, Tag
from .constants import HISTORY_BY_TERM_URL, ACADEMIC_URL


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
