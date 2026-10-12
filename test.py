from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument("--start-maximized")

driver = webdriver.Chrome(options=options)

driver.get("https://www.foundit.in/")

print("URL:", driver.current_url)
print("TITLE:", driver.title)

input("Press ENTER to close...")

driver.quit()