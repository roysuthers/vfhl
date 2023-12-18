import os
import sys
import traceback
from pathlib import Path
from selenium.webdriver import Firefox
# from selenium.webdriver import DesiredCapabilities
from selenium.webdriver.firefox.options import Options

import PySimpleGUI as sg

class Browser:

    def __enter__(self):

        self.browser = self.setBrowserOptions()

        return self.browser

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.browser.close()

        return

    def setBrowserOptions(self):

        # Constants
        PROFILE_PATH = Path('C:/Users/Roy/AppData/Roaming/Mozilla/Firefox/Profiles/wafmugwl.Fantrax')
        DRIVER_NAME = 'geckodriver.exe'

        try:
            options = Options()
            options.headless = True
            options.profile = str(PROFILE_PATH)
            driver_path  = Path(os.getcwd()) / DRIVER_NAME
            self.browser = Firefox(executable_path=str(driver_path) , options=options)

            self.browser.set_page_load_timeout(30)  # Set timeout to 10 seconds

        except FileNotFoundError:
            raise Exception(f"Driver not found: {driver_path}")

        except Exception as e:
            sg.popup_error_with_traceback(sys._getframe().f_code.co_name, 'Exception: ', ''.join(traceback.format_exception(type(e), value=e, tb=e.__traceback__)))
            return None

        return self.browser
