from utils import *
from tkinter import Tk, Label, Button, Entry
import threading
from time import sleep
import logging
import openpyxl
import os.path
import random
import re
from selenium.common.exceptions import TimeoutException

handlers = [logging.FileHandler('error.log'), logging.StreamHandler()]
logging.basicConfig(handlers=handlers, level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = 'https://pro.imdb.com'
NCONST_RE = re.compile(r'/name/(nm\d+)')

FILENAME = 'data.xlsx'
HEADER = ['Actor Name', 'Star Meter', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent', 'LawFirm', 'Lawyer']

# Every profile page carries its data as JSON, read only the parts that are needed instead of a dozen XPaths
PROFILE_JS = """
const props = window.__NEXT_DATA__.props.pageProps;
const above = props.aboveTheFold || {};
const sidebar = props.sidebarData || {};
return {aboveTheFold: {nameText: above.nameText, meterRank: above.meterRank},
        sidebarData: {representation: sidebar.representation}};
"""


def find_target_profile(driver, name_value):
    xpaths = [ImdbXpaths.TARGETED_PROFILE_1.format(name_value), ImdbXpaths.TARGETED_PROFILE.format(name_value), ImdbXpaths.TARGETED_PROFILE_2.format(name_value)]

    def find_or_scroll(d):
        for xpath in xpaths:
            found = d.find_elements(By.XPATH, xpath)
            if found:
                return found[0]
        # Not in the current view, scroll a little so the next try looks further down the results
        d.execute_script('window.scrollBy(0, Math.round(window.innerHeight * 0.5));')
        return None

    try:
        return WebDriverWait(driver, 30).until(find_or_scroll)
    except TimeoutException:
        return None


def get_client_urls(driver):
    cards = driver.find_elements(By.XPATH, ImdbXpaths.CLIENT_LIST)
    return driver.execute_script('return arguments[0].map(a => a.href)', cards) if cards else []


def load_more_clients(driver, loaded):
    """Click the "See all" button of the clients list and wait for the new clients, False if there are no more."""
    if not driver.find_elements(By.XPATH, ImdbXpaths.NEXT_BTN):
        return False
    btn_click_with_action_chains(driver, ImdbXpaths.NEXT_BTN)
    try:
        WebDriverWait(driver, 15).until(lambda d: len(d.find_elements(By.XPATH, ImdbXpaths.CLIENT_LIST)) > loaded)
    except TimeoutException:
        return False
    return True


def scrape_client(driver, url):
    driver.get(url)
    WebDriverWait(driver, 20).until(lambda d: d.execute_script('return !!window.__NEXT_DATA__'))
    return driver.execute_script(PROFILE_JS)


def _agent_names(agency):
    names = []
    for agent in (agency or {}).get('agents') or []:
        text = (((agent.get('name') or {}).get('nameText')) or {}).get('text')
        if text:
            names.append(text)
    return names


def parse_client_profile(page_props):
    """Return the spreadsheet row for a client profile, or None if the client has a manager."""
    representations = [edge['node'] for edge in (page_props['sidebarData'].get('representation') or {}).get('edges') or []]
    kinds = [((node.get('relationshipType') or {}).get('text') or '') for node in representations]
    if any('manager' in kind.lower() for kind in kinds):
        return None

    actor_name = page_props['aboveTheFold']['nameText']['text']
    rank = (page_props['aboveTheFold'].get('meterRank') or {}).get('currentRank')
    star_meter = f'{rank:,}' if rank else ''

    agencies = []
    law_firms = []
    lawyers = []
    for node, kind in zip(representations, kinds):
        agency = node.get('agency')
        company = (((agency or {}).get('company') or {}).get('companyText') or {}).get('text') or ''
        names = _agent_names(agency)
        if 'talent agent' in kind.lower() or 'theatrical' in kind.lower():
            agencies.append((company, ''.join(f'{name} \n' for name in names)))
        elif 'legal' in kind.lower():
            if company:
                law_firms.append(company)
            lawyers.extend(names)

    content = [actor_name, star_meter]
    for i in range(4):
        content.extend(agencies[i] if i < len(agencies) else ('', ''))
    content.append('\n'.join(law_firms))
    content.append(''.join(f'{name} \n' for name in lawyers))
    return content


def open_workbook():
    if os.path.isfile(FILENAME):
        return openpyxl.load_workbook(FILENAME)
    wb = openpyxl.Workbook()
    wb.active.append(HEADER)
    return wb


def main(name_value, profile_count):
    if name_value == '':
        logging.info('Name field is empty. Please enter a valid name.')
        return
    if not profile_count.isdigit() or int(profile_count) == 0:
        logging.info('Profile Count field is empty. Please enter a valid profile count.')
        return
    wanted_profiles = int(profile_count)
    driver = get_normal_driver_with_user_directory()
    try:
        insert_value_and_press_enter(driver, ImdbXpaths.SEARCH_BOX, name_value, previouse_clear=True)
        target_profile = find_target_profile(driver, name_value)
        if target_profile is None:
            logging.info(f'{name_value} is not present on proImdb, Try a different Name.')
            return

        nconst = NCONST_RE.search(target_profile.get_attribute('href') or '')
        if nconst is None:
            logging.info(f'Could not read the profile id of {name_value}.')
            return
        driver.get(f'{BASE_URL}/name/{nconst.group(1)}/clients/?ref_=nmovr')
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, ImdbXpaths.CLIENT_LIST)))
        except TimeoutException:
            logging.info(f'{name_value} do not have client on his profile.')
            return

        # The clients list stays open in its own tab, the profiles are loaded one after another in a second tab
        client_urls = get_client_urls(driver)
        clients_tab = driver.current_window_handle
        driver.switch_to.new_window('tab')
        profile_tab = driver.current_window_handle

        workbook = open_workbook()
        valid_profiles = 0
        checked_profiles = 0
        index = 0
        while valid_profiles < wanted_profiles:
            if index == len(client_urls):
                # Every loaded client was checked, load the next ones only now
                driver.switch_to.window(clients_tab)
                try:
                    loaded = load_more_clients(driver, len(client_urls))
                except Exception as e:
                    logging.info(f'Error: {e}')
                    loaded = False
                if not loaded:
                    break
                client_urls = get_client_urls(driver)
                logging.info(f'Clients Loaded: {len(client_urls)}')
                driver.switch_to.window(profile_tab)
            url = client_urls[index]
            index += 1
            try:
                sleep(random.uniform(1, 2))
                content = parse_client_profile(scrape_client(driver, url))
                checked_profiles += 1
                logging.info(f'Checked Profiles: {checked_profiles}')
                if content is None:
                    continue
                workbook.active.append(content)
                workbook.save(FILENAME)
                valid_profiles += 1
                print(f"********************** Number of profiles have been scraped: {valid_profiles} **********************")
                print(" ")
                print(f"-> Nummber of profiles left to scrape: {wanted_profiles - valid_profiles}")
            except Exception as e:
                print(f'Error: {e}')
                continue

        logging.info(f'Successfully scraped {valid_profiles} profiles for {name_value}.')
    except Exception as e:
        logging.info(f'Error occurred: {e}')
    finally:
        driver.quit()


class FormFillingBotGUI:

    def __init__(self, master):
        self.name_label = Label(master, text='Input Name')
        self.name_field = Entry(master, width=30)
        self.profile_count_label = Label(master, text='Profile Count')
        self.profile_count_field = Entry(master, width=10)
        self.start = Button(master, text="Start",
                            command=self.start, width=20)
        self.quit = Button(master, text="Stop", width=20,
                           command=lambda: master.destroy())

        master.geometry("360x120")
        master.minsize(360, 120)
        master.maxsize(360, 120)

        self.name_label.grid(row=1, column=0)
        self.name_field.grid(row=1, column=1)
        self.profile_count_label.grid(row=2, column=0)
        self.profile_count_field.grid(row=2, column=1)

        self.start.grid(row=4, column=1)
        self.quit.grid(row=5, column=1)

    def start(self):
        name = self.name_field.get()
        profile_count = self.profile_count_field.get()

        if not (name):
            self.name_field.focus()

        else:
            t = threading.Thread(target=main, args=(name, profile_count))
            t.daemon = True
            t.start()


if __name__ == '__main__':
    root = Tk()
    my_gui = FormFillingBotGUI(root)
    root.mainloop()
