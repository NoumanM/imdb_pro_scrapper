from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from pathlib import Path
from selenium_stealth import stealth
from selenium.webdriver.common.action_chains import ActionChains

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

def scroll_to_end_of_page(driver):
    # Scroll to the end of the page
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait for the page to load
        WebDriverWait(driver, 2).until(lambda d: True)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height


def btn_click_with_action_chains(driver, xpath, wait_time=10):
    element = WebDriverWait(driver, wait_time).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    action = ActionChains(driver)
    action.move_to_element(element).perform()
    action.click(element).perform()

class ImdbXpaths:
    SEARCH_BOX = "//input[@placeholder='Search and Discover']"
    TARGETED_PROFILE = '(//li/following-sibling::li[not(contains(text(), "Actress")) and not(contains(text(), "Actor")) and ((contains(text(), "Legal")) or(contains(text(), "Talent")))]//parent::ul//span[contains(@class,"display-name") or contains(@class,"display-company")]//a[text()="{0}"])[1]'
    CLIENTS_BTN = "//li[@data-a-tab-name='clients']/a | //h3[contains(text(),'Clients')] | //a[contains(@href, '/clients/')]"
    NEXT_BTN = "//span[contains(text(),' Show next')]/preceding-sibling::input | //span[contains(@class, 'ipc-see-more__text')]/ancestor::button"
    CLIENT_LIST = "//td[@class='client_profile']/div/div/div/div[2]//span[contains(@class, 'const_full_name')]/a | //table[@id='company_clients']//tr[position()>1]//span[@class='a-size-base-plus']/parent::a | //li[@data-testid='client-card']/div/div/div/a[contains(@href, '/name/')]"
    MANAGER_XPATH = "//span[contains(text(),' Manager')] | //span[contains(text(),'Manager')]"
    ACTOR_NAME_XPATH = "//h1//span"
    STAR_RATING_XPATH = "(//span[contains(text(),' STARmeter:')]/following-sibling::span)[1] | (//span[@aria-label='STARmeter']/following-sibling::span)[2]"
    TALENT_AGENT_BLOCKS = "//span[contains(text(),' Talent Agent')] | //span[contains(text(),'Talent Agent')]"
    LAW_FIRM_XPATH = "//span[contains(text(),'Legal Representative')]/../../following-sibling::div/ul[1]/li[2]//a | //span[contains(text(),'Legal Representative')]/../../following-sibling::div//ul[1]//button/preceding-sibling::span"
    LAWYER_NAME_XPATH = "//span[contains(text(),'Legal Representative')]/../../following-sibling::div//p//span[contains(text(),'Representatives')]/../../following-sibling::ul//span[contains(@class,'glyphicons glyphicons-icon')]/../span[last()]//a | //span[contains(text(),'Legal Representative')]/../../following-sibling::div//li//a"
