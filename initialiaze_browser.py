import os

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
os.system(f"start \"\" \"{chrome_path}\" --user-data-dir=\"%cd%\cd\" --window-position=0,0")