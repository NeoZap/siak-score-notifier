from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webdriver import WebDriver
from webdriver_manager.chrome import ChromeDriverManager

from siak.constants import SELENIUM_HUB_URL


def init_webdriver(is_docker_env: bool = False) -> WebDriver:
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--ignore-ssl-errors=yes")
    chrome_options.add_argument("--ignore-certificate-errors")
    if is_docker_env:
        return webdriver.Remote(
            command_executor=SELENIUM_HUB_URL, options=chrome_options
        )
    else:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(options=chrome_options, service=service)
