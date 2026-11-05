from utils import *
from tkinter import Tk, Label, Button, Entry
import threading
from time import sleep
import json
import logging
import openpyxl
import os.path
import random
import re
import requests

handlers = [logging.FileHandler('error.log'), logging.StreamHandler()]
logging.basicConfig(handlers=handlers, level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = 'https://pro.imdb.com'
GRAPHQL_URL = 'https://api.graphql.imdb.com/'
# Persisted query of the "See all" button on the clients page, IMDb changes it when the site is redeployed
CLIENTS_QUERY_HASH = '6770724f2f3b4d99152bcb8e3b0db0072ca73f295cdc507c2b2aa3a92473f0ac'
GRAPHQL_WEBLAB_OVERRIDES = json.dumps({
    'IMDB_1360659': 'T1', 'IMDB_ADS_CXM_EIDS_1402488': 'T1', 'IMDB_DISCO_KNOWNFOR_V2_1328450': 'T1',
    'IMDB_JANET_CACHE_1429668': 'T1', 'IMDB_PAP_AAP_CONVERSION_WEB_1400915': 'T1',
    'IMDB_PRODUCER_CREDITS_DISPLAY_DEFAULT_1377204': 'T1', 'IMDB_PRO_CONN_MASTER_1372979': 'T1',
    'IMDB_SEARCH_DISCOVER_MODERN_1367402': 'T2'})
NEXT_DATA_RE = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)
NCONST_RE = re.compile(r'/name/(nm\d+)')

FILENAME = 'data.xlsx'
HEADER = ['Actor Name', 'Star Meter', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent', 'LawFirm', 'Lawyer']


def sync_cookies(session, driver):
    session.cookies.clear()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain', ''), path=cookie.get('path', '/'))


def build_session(driver):
    session = requests.Session()
    session.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
        # Same UA the browser session (and its aws-waf-token) was created with
        'User-Agent': driver.execute_script('return navigator.userAgent'),
    })
    sync_cookies(session, driver)
    return session


def fetch_page_props(session, driver, url, referer):
    """GET a pro.imdb.com page and return the pageProps of its embedded __NEXT_DATA__ JSON.

    If the response is not the real page (WAF challenge, expired token), the browser is
    pointed at the same url to refresh the cookies and the request is retried once.
    """
    for attempt in range(2):
        response = session.get(url, headers={'Referer': referer}, timeout=30)
        match = NEXT_DATA_RE.search(response.text) if response.status_code == 200 else None
        if match:
            return json.loads(match.group(1))['props']['pageProps']
        if attempt == 0:
            logging.info(f'HTTP {response.status_code} without page data for {url}, refreshing cookies from the browser.')
            driver.get(url)
            sleep(5)
            sync_cookies(session, driver)
    raise RuntimeError(f'Could not load {url} (HTTP {response.status_code})')


def parse_clients(clients):
    """Return ([(nconst, name), ...], end cursor, has next page) for a `clients` connection.

    The connection embedded in the HTML has no hasNextPage, so it is derived from the total.
    """
    found = []
    for edge in clients.get('edges') or []:
        client = edge['node']['client']
        found.append((client['id'], client['nameText']['text']))
    page_info = clients.get('pageInfo') or {}
    end_cursor = page_info.get('endCursor')
    has_next = page_info.get('hasNextPage', clients.get('total', 0) > len(found))
    return found, end_cursor, bool(end_cursor and has_next)


def fetch_clients_page(session, driver, nconst, after, referer, request_id, page_size=20):
    """Load the next page of clients, the request behind the "See all" button, from the GraphQL API.

    request_id is the requestId of the clients page the browser had loaded.

    Returns (total, [(nconst, name), ...], end cursor, has next page).
    """
    variables = {'after': after, 'const': nconst, 'first': page_size, 'isOwnPage': False, 'locale': 'en-US',
                 'sort': {'by': 'POPULARITY', 'order': 'ASC'}}
    extensions = {'persistedQuery': {'sha256Hash': CLIENTS_QUERY_HASH, 'version': 1}}
    params = {'operationName': 'NameClientsSubPagePage',
              'variables': json.dumps(variables, separators=(',', ':')),
              'extensions': json.dumps(extensions, separators=(',', ':'))}
    for attempt in range(2):
        headers = {
            'Accept': 'application/graphql+json, application/json',
            'Content-Type': 'application/json',
            'Origin': BASE_URL,
            'Referer': referer,
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'x-amzn-sessionid': session.cookies.get('session-id', ''),
            'x-imdb-client-name': 'imdb-web-next-localized',
            'x-imdb-client-rid': request_id,
            'x-imdb-consent-info': session.cookies.get('ci', ''),
            'x-imdb-user-country': 'US',
            'x-imdb-user-language': 'en-US',
            'x-imdb-weblab-treatment-overrides': GRAPHQL_WEBLAB_OVERRIDES,
        }
        response = session.get(GRAPHQL_URL, params=params, headers=headers, timeout=30)
        try:
            clients = response.json()['data']['name']['clients']
        except (ValueError, KeyError, TypeError):
            clients = None
        if clients:
            found, end_cursor, has_next = parse_clients(clients)
            return clients.get('total', 0), found, end_cursor, has_next
        if attempt == 0:
            logging.info(f'HTTP {response.status_code} without clients from the GraphQL API, refreshing cookies from the browser.')
            sync_cookies(session, driver)
    raise RuntimeError(f'Could not load more clients (HTTP {response.status_code}): {response.text[:200]}')


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


def save_row(content):
    if not os.path.isfile(FILENAME):
        wb = openpyxl.Workbook()
        wb.active.append(HEADER)
        wb.save(FILENAME)

    wb = openpyxl.load_workbook(FILENAME)
    wb.active.append(content)
    wb.save(FILENAME)


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
        sleep(2)
        insert_value_and_press_enter(driver, ImdbXpaths.SEARCH_BOX, name_value, previouse_clear=True)
        sleep(5)
        result_of_searched_profile = driver.find_elements(By.XPATH, ImdbXpaths.TARGETED_PROFILE_1.format(name_value))
        if not result_of_searched_profile:
            result_of_searched_profile = driver.find_elements(By.XPATH, ImdbXpaths.TARGETED_PROFILE.format(name_value))
        if not result_of_searched_profile:
            logging.info(f'{name_value} is not present on proImdb, Try a different Name.')
            return

        result_of_searched_profile[0].click()
        WebDriverWait(driver, 20).until(lambda d: NCONST_RE.search(d.current_url))
        profile_url = driver.current_url
        nconst = NCONST_RE.search(profile_url).group(1)

        # From here on everything is plain HTTP, authenticated with the browser's cookies
        session = build_session(driver)
        clients_url = f'{BASE_URL}/name/{nconst}/clients/?ref_=nmovr'
        page_props = fetch_page_props(session, driver, clients_url, profile_url)
        clients_info = (page_props.get('mainColumnData') or {}).get('clients') or {}
        total_clients = clients_info.get('total', 0)
        clients, end_cursor, has_next = parse_clients(clients_info)
        if not clients:
            logging.info(f'{name_value} do not have client on his profile.')
            return
        logging.info(f'{name_value} has {total_clients} clients.')
        request_id = page_props['requestContext']['requestId']

        valid_profiles = 0
        checked_profiles = 0
        index = 0
        while valid_profiles < wanted_profiles:
            if index == len(clients):
                # Every loaded client was checked, load the next page like the "See all" button does
                if not has_next:
                    break
                try:
                    sleep(random.uniform(1, 2))
                    _, more_clients, end_cursor, has_next = fetch_clients_page(session, driver, nconst, end_cursor, clients_url, request_id)
                except Exception as e:
                    logging.info(f'Error: {e}')
                    break
                if not more_clients:
                    break
                clients.extend(more_clients)
                logging.info(f'Clients Loaded: {len(clients)} of {total_clients}')
            client_id, client_name = clients[index]
            index += 1
            try:
                sleep(random.uniform(1, 2))
                client_props = fetch_page_props(session, driver, f'{BASE_URL}/name/{client_id}/?ref_=nmcl_cl_{index}', clients_url)
                checked_profiles += 1
                logging.info(f'Checked Profiles: {checked_profiles} ({client_name})')
                content = parse_client_profile(client_props)
                if content is None:
                    continue
                save_row(content)
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
