import os
import traceback
from pathlib import Path
from selenium.webdriver import Firefox
from selenium.webdriver.firefox.options import Options

# Constants
PROFILE_PATH = Path('C:/Users/Roy/AppData/Roaming/Mozilla/Firefox/Profiles/wafmugwl.Fantrax')
DRIVER_NAME = 'geckodriver.exe'

def setBrowserOptions():

    try:
        options = Options()
        options.headless = True
        options.profile = str(PROFILE_PATH)
        driver_path  = Path(os.getcwd()) / DRIVER_NAME
        driver = Firefox(executable_path=str(driver_path) , options=options)

    except Exception as e:
        raise

    return driver
