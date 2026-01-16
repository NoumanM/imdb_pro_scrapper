from utils import *
from tkinter import Tk, Label, Button, Entry, IntVar, StringVar, OptionMenu, Checkbutton
import threading
from time import sleep
from selenium.webdriver.common.by import By
import logging
import openpyxl
import os.path

handlers = [logging.FileHandler('error.log'), logging.StreamHandler()]
logging.basicConfig(handlers=handlers, level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

row = 0
column = 0

def main(name_value, profile_count):
    if name_value == '':
        logging.info('Name field is empty. Please enter a valid name.')
        return
    if profile_count == '':
        logging.info('Profile Count field is empty. Please enter a valid profile count.')
        return
    global row
    global column
    driver = get_normal_driver_with_user_directory()
    sleep(2)
    insert_value_and_press_enter(driver, ImdbXpaths.SEARCH_BOX, name_value, previouse_clear=True)
    sleep(5)
    try:
        result_of_searched_profile = driver.find_elements(By.XPATH, ImdbXpaths.TARGETED_PROFILE.format(name_value))
        if result_of_searched_profile:
            result_of_searched_profile[0].click()
            sleep(3)
            clients = driver.find_elements(By.XPATH, ImdbXpaths.CLIENTS_BTN)
            if clients:
                clients[0].click()
                sleep(5)
                while True:
                    scroll_to_end_of_page(driver)
                    next_button = driver.find_elements(By.XPATH, ImdbXpaths.NEXT_BTN)
                    sleep(2)
                    if next_button:
                        btn_click_with_action_chains(driver, ImdbXpaths.NEXT_BTN)
                        sleep(5)
                        number_of_clients = driver.find_elements(By.XPATH, ImdbXpaths.CLIENT_LIST)
                        if len(number_of_clients) > 20 * int(profile_count):
                            logging.error(f"Total Profiles Loaded: {len(number_of_clients)}")
                            sleep(2)
                            break
                    else:
                        break
                valid_profiles = 0
                checked_profiles = 0
                number_of_clients = driver.find_elements(By.XPATH, ImdbXpaths.CLIENT_LIST)
                for client in number_of_clients:
                    try:
                        if valid_profiles == int(profile_count):
                                break
                        client_profile_url = client.get_attribute('href')
                        sleep(2)
                        driver.execute_script(f"window.open('{client_profile_url}','_blank')")
                        main_tab = driver.current_window_handle
                        window_handles = driver.window_handles
                        for handle in window_handles:
                            try:
                                if handle != main_tab:
                                    driver.switch_to.window(handle)
                                    break
                                name = driver.find_element(By.XPATH, ImdbXpaths.ACTOR_NAME_XPATH)
                                print("Page Name: " + name.get_attribute('innerText'))

                            except:
                                print('Error: Switching Tab')
                                continue

                        sleep(2)
                        checked_profiles += 1
                        logging.error(f"Checked Profiles: {checked_profiles}")
                        do_not_have_manager = driver.find_elements(By.XPATH, ImdbXpaths.MANAGER_XPATH)
                        if not do_not_have_manager:
                            valid_profiles += 1
                            item = {}
                            actor_name = (driver.find_elements(By.XPATH, ImdbXpaths.ACTOR_NAME_XPATH))[0].get_attribute('innerText')
                            sleep(1)
                            start_meter = (driver.find_elements(By.XPATH, ImdbXpaths.STAR_RATING_XPATH))[0].get_attribute('innerText').strip()
                            j = 0
                            k = 1
                            agency_1 = ''
                            agency_2 = ''
                            agency_3 = ''
                            agency_4 = ''
                            talent_agent_1 = ''
                            talent_agent_2 = ''
                            talent_agent_3 = ''
                            talent_agent_4 = ''
                            lawyer = ''
                            law_firm = ''
                            talent_agent_blocks = driver.find_elements(By.XPATH, ImdbXpaths.TALENT_AGENT_BLOCKS)
                            for i in talent_agent_blocks:
                                try:
                                    talent_agent_exist = i.get_attribute('innerText').strip()  #j =1
                                    j +=1
                                    if 'talent agent' in talent_agent_exist.lower() or 'theatrical' in talent_agent_exist.lower():
                                        item[f'Agency {k}'] = driver.find_element(By.XPATH, f"(//span[contains(text(),' Talent Agent')]/../../following-sibling::div/ul[1]/li[2]//a)[{j}] | (//span[contains(text(),'Talent Agent')]/../../following-sibling::div//ul//button[1]/preceding-sibling::span)[{j}]").get_attribute('innerText')
                                        k += 1
                                        agency_1 = str(item[f'Agency 1']) if k == 2 else agency_1
                                        agency_2 = str(item['Agency 2']) if k == 3 else agency_2
                                        agency_3 = str(item['Agency 3']) if k == 4 else agency_3
                                        agency_4 = str(item['Agency 4']) if k == 5 else agency_4

                                        i = 1
                                        for r in driver.find_elements(By.XPATH, f"(//span[contains(text(),' Talent Agent')])[{j}]/../../following-sibling::div/p//span[contains(text(),' Representatives')]/../../following-sibling::ul/li//span[contains(@class,'glyphicons-user text_color_stone')]/../span//a[contains(@href,'https')] | (//span[contains(text(),'Talent Agent')])[{j}]/../../following-sibling::div//ul/li//a[contains(@href, 'contact_repr')]"):
                                            item[f'Talent Agent {i}'] = r.get_attribute('innerText')
                                            if j == 1:
                                                talent_agent_1 = talent_agent_1 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                            if j == 2:
                                                talent_agent_2 = talent_agent_2 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                            if j == 3:
                                                talent_agent_3 = talent_agent_3 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                            if j == 4:
                                                talent_agent_4 = talent_agent_4 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                            i += 1
                                except:
                                    print('Error: Talent Agent Info')
                                    continue

                            for q in driver.find_elements(By.XPATH, ImdbXpaths.LAW_FIRM_XPATH):
                                try:
                                    law_firm = q.get_attribute('innerText')
                                except:
                                    law_firm = ''
                                    print('Error: Law Firm Info')
                                    continue
                            n = 1
                            for r in driver.find_elements(By.XPATH, ImdbXpaths.LAWYER_NAME_XPATH):
                                try:
                                    item[f"Lawyer {n}"] = r.get_attribute('innerText')
                                    lawyer = lawyer + item[f"Lawyer {n}"] + " "+"\n"
                                    n += 1
                                except:
                                    print('Error: Lawyer Info')
                                    continue

                            filename = 'data.xlsx'
                            file_exists = os.path.isfile(filename)

                            header = ['Actor Name', 'Star Meter', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent','LawFirm', 'Lawyer']
                            content = [actor_name, start_meter, agency_1, talent_agent_1, agency_2, talent_agent_2, agency_3, talent_agent_3, agency_4, talent_agent_4, law_firm, lawyer]
                            if not file_exists:
                                wb = openpyxl.Workbook()
                                ws = wb.active
                                ws.append(header)
                                wb.save(filename)

                            wb = openpyxl.load_workbook(filename)
                            ws = wb.active
                            ws.append(content)
                            wb.save(filename)


                            actor_name =  start_meter =  agency_1= talent_agent_1= agency_2= talent_agent_2= agency_3= talent_agent_3= agency_4= talent_agent_4=  law_firm= lawyer = ''
                            sleep(2)
                            driver.close()
                            print(f"********************** Number of profiles have been scraped: {valid_profiles} **********************")
                            print(" ")
                            print(f"-> Nummber of profiles left to scrape: {int(profile_count) - valid_profiles}")
                            driver.switch_to.window(main_tab)

                        else:
                            sleep(2)
                            driver.close()
                            driver.switch_to.window(main_tab)

                    except Exception as e:
                        print(f'Error: {e}')
                        try:
                            driver.close()
                            driver.switch_to.window(main_tab)
                        except:
                            pass
                        continue

                try:
                    logging.info(f'Successfully scraped {valid_profiles} profiles for {name_value}.')
                    driver.quit()
                except:
                    pass
            else:
                logging.info(f'{name_value} do not have client on his profile.')
                driver.quit()
        else:
            logging.info(f'{name_value} is not present on proImdb, Try a different Name.' )
            driver.quit()
    except Exception as e:
        logging.info(f'Error occurred: {e}')
        driver.quit()
        return


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
        global cancel_flag
        cancel_flag = 0
        # #prev##
        name = self.name_field.get()
        profile_count = self.profile_count_field.get()

        if not (name):
            self.name_field.focus()

        else:
            t = threading.Thread(target = main, args=(name, profile_count))
            t.daemon = True
            t.start()

    def quit(self, master):
        master.destroy()

if __name__ == '__main__':
    root = Tk()
    my_gui = FormFillingBotGUI(root)
    root.mainloop()

