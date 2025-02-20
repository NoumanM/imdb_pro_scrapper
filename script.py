from utils import get_normal_driver_with_user_directory, insert_value_and_press_enter, scroll_to_element_smoothly
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
    global row
    global column
    driver = get_normal_driver_with_user_directory()
    sleep(2)
    insert_value_and_press_enter(driver, "//input[@placeholder='Search and Discover']", name_value, previouse_clear=True)
    sleep(5)
    result_of_searched_profile = driver.find_elements(By.XPATH, f'(//li/following-sibling::li[not(contains(text(), "Actress"))]//parent::li//span[contains(@class,"display-name") or contains(@class,"display-company")]//a[text()="{name_value}"])[1]')
    if len(result_of_searched_profile) != 0:
        result_of_searched_profile[0].click()
        sleep(3)
        clients = driver.find_elements(By.XPATH, "//li[@data-a-tab-name='clients']/a | //h3[contains(text(),'Clients')]")
        if len(clients) != 0:
            clients[0].click()
            sleep(5)
            while True:
                next_button = driver.find_elements(By.XPATH, "//span[contains(text(),' Show next')]/preceding-sibling::input")
                if next_button:
                    scroll_to_element_smoothly(driver, "//span[contains(text(),' Show next')]/preceding-sibling::input")
                    next_button[0].click()
                    sleep(5)
                else:
                    break

            valid_profiles = 0
            checked_profiles = 0
            number_of_clients = driver.find_elements(By.XPATH, "//td[@class='client_profile']/div/div/div/div[2]//span[contains(@class, 'const_full_name')]/a | //table[@id='company_clients']//tr[position()>1]//span[@class='a-size-base-plus']/parent::a")
            for client in number_of_clients:
                if valid_profiles == int(profile_count):
                        break
                client_profile_url = client.get_attribute('href')
                sleep(2)
                driver.execute_script(f"window.open('{client_profile_url}','_blank')")
                main_tab = driver.current_window_handle
                chwd = driver.window_handles
                for w in chwd:
                    if w != main_tab:
                        driver.switch_to.window(w)
                        break
                sleep(2)
                checked_profiles += 1
                logging.error(f"Checked Profiles: {checked_profiles}")
                do_not_have_manager = driver.find_elements(By.XPATH, "//span[contains(text(),' Manager')]")
                if len(do_not_have_manager) == 0:
                    
                    valid_profiles += 1
                    
                    item = {}
                    actor_name = (driver.find_elements(By.XPATH, "//h1//span"))[0].text.strip()
                    sleep(1)
                    start_meter = (driver.find_elements(By.XPATH, "(//span[contains(text(),' STARmeter:')]/following-sibling::span)[1]"))[0].text.strip()
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
                    larfirm = ''
                    for i in driver.find_elements(By.XPATH, "//span[contains(text(),' Talent Agent')]"):
                        talent_agent_exist = i.text.strip()  #j =1
                        j +=1
                        if talent_agent_exist == 'Talent Agent' or talent_agent_exist == 'Talent Agent Theatrical':
                            item[f'Agency {k}'] = driver.find_element(By.XPATH, f"(//span[contains(text(),' Talent Agent')]/../../following-sibling::div/ul[1]/li[2]//a)[{j}]").get_attribute('text')
                            k += 1
                            if k == 2:
                                agency_1 = str(item[f'Agency 1'])
                            if k == 3:
                                agency_2 = str(item['Agency 2'])
                            if k == 4:
                                agency_3 = str(item['Agency 3'])
                            if k == 5:
                                agency_4 = str(item['Agency 4'])

                            i = 1
                            for r in driver.find_elements(By.XPATH, f"(//span[contains(text(),' Talent Agent')])[{j}]/../../following-sibling::div/p//span[contains(text(),' Representatives')]/../../following-sibling::ul/li//span[contains(@class,'glyphicons-user text_color_stone')]/../span//a[contains(@href,'https')]"):
                                item[f'Talent Agent {i}'] = r.get_attribute('text')
                                if j == 1:
                                    talent_agent_1 = talent_agent_1 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                if j == 2:
                                    talent_agent_2 = talent_agent_2 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                if j == 3:
                                    talent_agent_3 = talent_agent_3 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                if j == 4:
                                    talent_agent_4 = talent_agent_4 + str(item[f'Talent Agent {i}']) +" "+ "\n"
                                i += 1
                    
                    for q in driver.find_elements(By.XPATH, "//span[contains(text(),'Legal Representative')]/../../following-sibling::div/ul[1]/li[2]//a"):
                        larfirm = q.get_attribute('text')
                    n = 1
                    for r in driver.find_elements(By.XPATH, "//span[contains(text(),'Legal Representative')]/../../following-sibling::div//p//span[contains(text(),'Representatives')]/../../following-sibling::ul//span[contains(@class,'glyphicons glyphicons-icon')]/../span[last()]//a"):
                        item[f"Lawyer {n}"] = r.get_attribute('text')
                        lawyer = lawyer + item[f"Lawyer {n}"] + " "+"\n"
                        n += 1

                    filename = 'data.xlsx'
                    file_exists = os.path.isfile(filename)
                    
                    header = ['Actor Name', 'Star Meter', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent', 'Agency', 'Agent','LawFirm', 'Lawyer']
                    content = [actor_name, start_meter, agency_1, talent_agent_1, agency_2, talent_agent_2, agency_3, talent_agent_3, agency_4, talent_agent_4, larfirm, lawyer]
                    if not file_exists:
                        wb = openpyxl.Workbook()
                        ws = wb.active
                        ws.append(header)
                        wb.save(filename)

                    wb = openpyxl.load_workbook(filename)
                    ws = wb.active
                    ws.append(content)
                    wb.save(filename)


                    actor_name =  start_meter =  agency_1= talent_agent_1= agency_2= talent_agent_2= agency_3= talent_agent_3= agency_4= talent_agent_4=  larfirm= lawyer = ''
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

            
            driver.quit()

        else:
            logging.info(f'{name_value} do not have client on his profile.')
            driver.quit()


    else:
        logging.info(f'{name_value} is not present on proImdb, Try a different Name.' )
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

