from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from pathlib import Path
from selenium_stealth import stealth

BASE_DIR = Path(__file__).resolve().parent


def get_normal_driver_with_user_directory(headless=False):
    try:
        # path = os.path.join(os.path.dirname(sys.executable), "cd")
        path = BASE_DIR / 'cd'
        print("Path for chrome directory", path)
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument("--log-level=3")
        options.add_argument(fr"--user-data-dir={path}")
        if headless:
            options.add_argument('--headless')
        options.add_argument('--start-maximized')
        driver = webdriver.Chrome(ChromeDriverManager().install(),options=options)

        stealth(driver,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.3',
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

        driver.get("https://pro.imdb.com/")
        return driver
    except Exception as e:
        print(e)
        print('------------------- Generation the New Driver')
        get_normal_driver_with_user_directory()


def insert_value_and_press_enter(driver, xpath, text, previouse_clear=False):
    element = WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.XPATH, xpath)))
    if previouse_clear:
        element.clear()
    element.send_keys(text)
    element.send_keys(Keys.ENTER)

def find_element(driver, by, sec, timeout=10):
    element = WebDriverWait(driver, timeout).until(
        EC.visibility_of_element_located((by, sec)))
    return element

def scroll_to_element_smoothly(driver, xpath):
    element = find_element(driver, By.XPATH, xpath)
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'nearest'})",
                          element)

