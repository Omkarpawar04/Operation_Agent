from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def start_browser():

    options = Options()

    options.add_argument("--start-maximized")

    options.binary_location = (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    )

    driver = webdriver.Chrome(options=options)

    return driver